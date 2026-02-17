import asyncio
import json
from typing import Awaitable, Callable

from dotenv import load_dotenv

from src.redis.client_redis import redis_client

load_dotenv()


BUFFER_TIMEOUT = 1  # segundos


def adicionar_ao_buffer(numero: str, nova_mensagem: str):
    """
    Adiciona uma mensagem ao buffer de um número específico.
    Reinicia o timer de timeout a cada nova mensagem.

    COMO FUNCIONA:
    - Pega todas as mensagens já armazenadas para esse número
    - Adiciona a nova mensagem à lista
    - Salva tudo de volta no Redis
    - Reinicia o timer de 10 segundos (setex = set with expiration)

    Args:
        numero (str): ID do usuário (número de telefone)
        nova_mensagem (str): A mensagem a ser adicionada
    """
    chave_conteudo = f'buffer:content:{numero}'
    chave_gatilho = f'buffer:trigger:{numero}'

    # Recupera as mensagens já armazenadas
    # Se não existir, começa com lista vazia
    mensagens_json = redis_client.get(chave_conteudo)
    mensagens = json.loads(mensagens_json) if mensagens_json else []

    # Adiciona a nova mensagem
    mensagens.append(nova_mensagem)

    # Salva as mensagens atualizadas
    redis_client.set(chave_conteudo, json.dumps(mensagens))

    # Reinicia o timer: a chave vai expirar em 10 segundos
    # O valor "1" é irrelevante, importante é que a chave expira
    redis_client.setex(chave_gatilho, BUFFER_TIMEOUT, 1)

    print(
        f'⏱️ Timer resetado para {numero} ({len(mensagens)} mensagens no buffer)'
    )


async def ouvinte_de_expiracao(
    callback: Callable[[str, str], Awaitable[None]],
):
    """
    Fica em loop ouvindo o Redis Pub/Sub esperando expirations de chaves.
    Quando uma chave buffer:trigger:{numero} expira, processa as mensagens.

    COMO FUNCIONA:
    1. Se inscreve no canal __keyevent@0__:expired do Redis
    2. Entra em loop infinito aguardando eventos
    3. Quando recebe um evento de uma chave buffer:trigger:
       - Extrai o número do usuário
       - Pega as mensagens agrupadas do Redis
       - Concatena com espaço
       - Chama a função callback (que invoca o agente)
       - Deleta as mensagens do Redis

    IMPORTANTE: Você precisa habilitar no Redis com:
    redis-cli CONFIG SET notify-keyspace-events Ex

    Args:
        callback: Função assíncrona que será chamada quando o timer expirar
                  Recebe (numero: str, texto_final: str)
    """
    print('🚀 Ouvinte de expiração iniciado...')

    # Se conecta ao Pub/Sub do Redis
    pubsub = redis_client.pubsub()

    # Se inscreve no canal de eventos de expiração
    # __keyevent@0__:expired = eventos de expiração da database 0
    pubsub.subscribe('__keyevent@0__:expired')

    while True:
        try:
            # Pega uma mensagem do Pub/Sub
            # ignore_subscribe_messages=True ignora confirmação de inscrição
            mensagem = pubsub.get_message(ignore_subscribe_messages=True)

            if mensagem and mensagem['data'].startswith('buffer:trigger:'):
                # Extrai o número da chave que expirou
                # Exemplo: "buffer:trigger:5585987654321" -> "5585987654321"
                numero = mensagem['data'].split(':')[2]
                chave_conteudo = f'buffer:content:{numero}'

                # Recupera as mensagens armazenadas
                mensagens_json = redis_client.get(chave_conteudo)

                if mensagens_json:
                    # Converte JSON para lista
                    mensagens_lista = json.loads(mensagens_json)

                    # Concatena todas as mensagens com espaço
                    # filter(None, ...) remove strings vazias
                    texto_final = ' '.join(
                        filter(None, map(str, mensagens_lista))
                    )

                    print(f'\n⏰ Timer expirou para {numero}')
                    print(
                        f'📦 Processando {len(mensagens_lista)} mensagem(ns)'
                    )
                    print(f'💬 Texto final: {texto_final}\n')

                    # Chama a função que invoca o agente
                    await callback(numero, texto_final)

                    # Limpa o buffer do Redis
                    redis_client.delete(chave_conteudo)
                    print(f'🗑️ Buffer deletado para {numero}\n')

            # Pequeno delay para não sobrecarregar a CPU
            await asyncio.sleep(0.01)

        except Exception as e:
            print(f'❌ Erro no ouvinte: {e}')
            await asyncio.sleep(
                1
            )  # Aguarda um pouco antes de tentar novamente


def iniciar_ouvinte_background(
    callback: Callable[[str, str], Awaitable[None]],
):
    """
    Inicia o ouvinte de expiração em uma thread separada.

    COMO FUNCIONA:
    - Cria uma thread daemon (encerra com a aplicação)
    - Roda o loop de ouvinte dentro dessa thread
    - Permite que o FastAPI continue respondendo requisições normalmente

    Args:
        callback: Função que será chamada quando mensagens expiram

    Returns:
        threading.Thread: A thread do ouvinte
    """
    import threading

    def executar_ouvinte():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(ouvinte_de_expiracao(callback))
        finally:
            loop.close()

    thread = threading.Thread(target=executar_ouvinte, daemon=True)
    thread.start()

    print('✅ Thread do ouvinte iniciada com sucesso!')
    return thread
