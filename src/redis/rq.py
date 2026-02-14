import os
from src.db.crud import PostgreSQL
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from rq import Queue, Retry

from redis import Redis
from src.graph.workflow import graph

load_dotenv()

# ============================================================================
# CONFIGURAÇÃO DO REDIS PARA RQ
# ============================================================================

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_PASSWORD = os.getenv('SENHA_REDIS')

# Conexão com Redis remoto
redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
)

# Cria a fila de tarefas
task_queue = Queue(connection=redis_conn)


# ============================================================================
# FUNÇÃO QUE SERÁ EXECUTADA PELO WORKER
# ============================================================================


def processar_agente(numero: str, texto_final: str):
    """
    Função que será executada em background pelo RQ Worker.

    COMO FUNCIONA:
    - RQ pega essa função e executa em um processo separado
    - Se falhar, RQ tenta novamente automaticamente (retry)
    - Os logs são capturados pelo RQ
    - O resultado fica armazenado no Redis

    Args:
        numero (str): Número do usuário
        texto_final (str): Mensagens concatenadas

    Returns:
        dict: Resultado do agente
    """
    try:
        print(f'📦 [WORKER] Processando buffer para: {numero}')
        print(f'💬 [WORKER] Texto agrupado: {texto_final}')

        # Monta a entrada para o agente
        entrada = {
            'number': numero,
            'messages': [HumanMessage(content=texto_final)],
        }

        # Invoca o agente LangGraph
        resultado = graph.invoke(entrada)
        # Extrai informações úteis
        if resultado.get('messages'):
            ultima_mensagem = resultado['messages'][-1]

            if hasattr(ultima_mensagem, 'content'):
                resposta_ia = ultima_mensagem.content
            else:
                resposta_ia = 'Sem resposta'

            metadata = getattr(ultima_mensagem, 'response_metadata', {})
            token_usage = metadata.get('token_usage', {})

            print(f'✅ [WORKER] Agente processou com sucesso para {numero}')
            print(f'\n{"=" * 60}')
            print(f'📝 Resposta IA: {resposta_ia}')
            print('\n📊 Métricas:')
            print(
                f'   • Tokens entrada: {token_usage.get("prompt_tokens", "N/A")}'
            )
            print(
                f'   • Tokens saída: {token_usage.get("completion_tokens", "N/A")}'
            )
            print(
                f'   • Total tokens: {token_usage.get("total_tokens", "N/A")}'
            )
            print(
                f'   • Tempo total: {metadata.get("total_time", "N/A"):.3f}s'
                if isinstance(metadata.get('total_time'), (int, float))
                else f'   • Tempo total: {metadata.get("total_time", "N/A")}'
            )
            print(f'   • Modelo: {metadata.get("model_name", "N/A")}')
            print(
                f'   • Motivo finalização: {metadata.get("finish_reason", "N/A")}'
            )
            print(f'{"=" * 60}\n')

            usage = getattr(ultima_mensagem, 'usage_metadata', None)

            if usage:
                PostgreSQL.save_tokens(
                    phone_number=numero,
                    message_id=ultima_mensagem.id,
                    input_tokens=usage.get('input_tokens', 0),
                    output_tokens=usage.get('output_tokens', 0),
                    total_tokens=usage.get('total_tokens', 0),
                    model_name=metadata.get('model_name'),
                    provider=metadata.get('model_provider'),
                )

                print('Tokens Salvos com Sucesso!!! \n')
                print(f'{"=" * 60}\n')

                
        return {'status': 'sucesso', 'numero': numero, 'resposta': resposta_ia}

    except Exception as e:
        print(f'❌ [WORKER] Erro ao processar mensagens para {numero}: {e}')
        print(
            f'Entrada que causou erro: number={numero}, texto={texto_final}\n'
        )

        # Re-lança a exceção pra RQ saber que falhou e tente novamente
        raise


def enqueue_agent_processing(numero: str, texto_final: str):
    """
    Coloca uma tarefa de processamento do agente na fila RQ.

    COMO FUNCIONA:
    - É chamada quando o buffer expira
    - Coloca a tarefa na fila do Redis
    - RQ pega a tarefa e executa no worker
    - Não bloqueia a aplicação

    Args:
        numero (str): Número do usuário
        texto_final (str): Mensagens concatenadas

    Returns:
        Job: Objeto da tarefa (pode ser usado pra rastrear status)
    """
    try:
        print(f'📤 Colocando tarefa na fila RQ para {numero}')

        # Coloca na fila com retry automático (max 3 tentativas)
        job = task_queue.enqueue(
            processar_agente,
            numero,
            texto_final,
            job_timeout=300,  # 5 minutos de timeout
            retry=Retry(max=3),  # Tenta até 3 vezes se falhar
        )

        print(f'✅ Tarefa enfileirada! Job ID: {job.id}\n')
        return job

    except Exception as e:
        print(f'❌ Erro ao enfileirar tarefa: {e}\n')
        raise
