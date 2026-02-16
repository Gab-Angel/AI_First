from contextlib import asynccontextmanager
from src.db.tables import create_tables
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from src.evo.client import EvolutionAPI
from src.agent.audio_transcription import audio_transcription
from src.db.crud import PostgreSQL
# Imports do seu projeto
from src.redis.buffer import adicionar_ao_buffer, iniciar_ouvinte_background
from src.redis.rq import enqueue_agent_processing
# ============================================================================
# FUNÇÃO QUE PROCESSA AS MENSAGENS AGRUPADAS (Callback do ouvinte)
# ============================================================================


async def processar_mensagens_agrupadas(numero: str, texto_final: str):
    """
    Callback chamado quando o timer do buffer expira.

    NOVO FLUXO COM RQ:
    1. Recebe número e texto agrupado do ouvinte Redis
    2. Coloca uma tarefa na fila RQ (não bloqueia)
    3. Um worker separado executa a tarefa
    4. Retorna imediatamente

    VANTAGENS:
    - Não bloqueia a aplicação
    - Retry automático se falhar
    - Worker pode estar em outro servidor
    - Melhor para produção

    Args:
        numero (str): ID do usuário
        texto_final (str): Mensagens concatenadas com espaço
    """
    try:
        print(f'📦 Buffer expirado para: {numero}')
        print(f'💬 Texto agrupado: {texto_final}')

        # Coloca na fila RQ (não executa agora, apenas enfileira)
        enqueue_agent_processing(numero, texto_final)

    except Exception as e:
        print(f'❌ Erro ao enfileirar processamento para {numero}: {e}\n')


# ============================================================================
# LIFESPAN: Inicializa e encerra a aplicação
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager que gerencia o ciclo de vida da aplicação FastAPI.

    STARTUP (yield):
    - Cria tabelas do banco de dados
    - Inicia o ouvinte de expiração do Redis em background

    SHUTDOWN (após yield):
    - Para a aplicação de forma controlada

    COMO FUNCIONA:
    1. Quando a app sobe, o código antes de 'yield' é executado
    2. A app roda normalmente
    3. Quando a app encerra, o código depois de 'yield' é executado
    """
    print('🚀 Inicializando aplicação...')

    # Se quiser criar tabelas automaticamente, descomente:
    create_tables()
    print("🟢 Banco pronto!")

    # Inicia o ouvinte em background
    # Passa a função que será chamada quando buffer expirar
    iniciar_ouvinte_background(processar_mensagens_agrupadas)

    print('✅ Sistema de buffer pronto!\n')

    yield  # Aplicação roda aqui

    print('🛑 Encerrando aplicação...')


# ============================================================================
# CRIAÇÃO DA APP FASTAPI
# ============================================================================

app = FastAPI(lifespan=lifespan)


# ============================================================================
# WEBHOOK: Recebe mensagens do WhatsApp
# ============================================================================


@app.post('/webhook')
async def webhook(request: Request):
    """
    Recebe mensagens do WhatsApp via webhook.

    FLUXO:
    1. Recebe dados do WhatsApp
    2. Extrai informações úteis (tipo de mensagem, conteúdo, número)
    3. Adiciona ao buffer Redis
    4. Timer começa/reinicia
    5. Retorna sucesso

    O processamento acontece automaticamente no background quando o timer expira.
    """
    try:
        data = await request.json()
        messageType = data['data'].get('messageType')

        key = data['data'].get('key', {})
        from_me = key.get('fromMe', False)

        # ========== EXTRAI O NÚMERO DO USUÁRIO ==========
        remoteJid = key.get('remoteJid')
        number = remoteJid.split('@')[0]

        if data:
            # ========== EXTRAI O TIPO DE MENSAGEM ==========
            if messageType == 'conversation':
                # Mensagem de texto normal
                message = data['data']['message'].get('conversation')

            elif messageType == 'imageMessage':
                message = 'Imagem enviada'

            elif messageType == 'audioMessage':
                audio_base64 = data['data']['message'].get('base64')

                if not audio_base64:
                    print("❌ Base64 do áudio não encontrado")
                    message = "[Áudio não processado]"
                else:
                    print('🎤 Processando Audio...')
                    try:
                        message = audio_transcription(audio_base64=audio_base64)
                    except Exception as e:
                        print(f"❌ Erro ao processar áudio: {e}")
                        message = "[Erro ao processar áudio]"

            else:
                # Tipo de mensagem não suportado
                message = None

            # ======================================================
            # 🔒 BLOQUEIO: MENSAGEM ENVIADA PELO PRÓPRIO SISTEMA
            # ======================================================
            if from_me:
                print('🤖 Mensagem enviada pela IA/Humano. Salvando e ignorando fluxo.')

                PostgreSQL.save_message(
                    session_id=number,
                    sender='human',  
                    message={'type': 'human', 'content': message}
                )

                return JSONResponse(
                    content={'status': 'mensagem da IA salva'},
                    status_code=200
                )

            print(f'📲 Mensagem de: {number}')
            print(f'💬 Conteúdo: {message}')

            # ========== GATEWAY: BLOQUEIO DA IA ==========
            user = PostgreSQL.get_user_by_number(number)

            if user and user.get("require_human") is True:
                print(f'🚫 IA bloqueada para {number} (humano no controle)')

                # Salva mensagem normalmente
                PostgreSQL.save_message(
                    session_id=number,
                    sender='user',
                    message={'type': 'user', 'content': message}
                )

                return JSONResponse(
                    content={'status': 'encaminhado_para_humano'},
                    status_code=200
                )

            # ========== ADICIONA AO BUFFER ==========
            adicionar_ao_buffer(number, message)

            print(f'➕ Mensagem adicionada ao buffer para {number}\n')

            return JSONResponse(
                content={'status': 'mensagem adicionada ao buffer'},
                status_code=200,
            )
        else:
            print('⚠️ Payload do webhook não continha os dados esperados.')
            return JSONResponse(
                content={'status': 'payload invalido'}, status_code=400
            )

    except Exception as e:
        print(f'❌ Erro no webhook: {e}')
        raise HTTPException(status_code=500, detail='erro interno')



@app.post('/scheduler')
async def scheduler_webhook(request: Request):
    
    try:
        payload = await request.json()
        
        print(f'\n{"="*60}')
        print(f'🔔 SCHEDULER DISPAROU - Enviando mensagem')
        print(f'{"="*60}')
        print(f'Payload recebido: {payload}')
        
        # Extrai os dados do payload
        numero = payload.get('numero')
        mensagem = payload.get('mensagem')
        
        if not numero or not mensagem:
            print('❌ Payload inválido: número ou mensagem ausente')
            raise HTTPException(status_code=400, detail='Número e mensagem são obrigatórios')
        
        print(f'📱 Número: {numero}')
        print(f'💬 Mensagem: {mensagem}')
        
        evo = EvolutionAPI()

        sender_message = evo.sender_text(
            number=numero,
            text=mensagem
        )

        if sender_message:
            message_payload = {'type': 'ai', 'content': mensagem}

            PostgreSQL.save_message(session_id=numero, message=message_payload)
            
            print('✅  Mensagem de Lembrete Salva no Banco')


        print(f'✅ Mensagem enviada com sucesso para {numero}!')
        print(f'{"="*60}\n')
        
        return JSONResponse(
            content={
                'status': 'enviado',
                'numero': numero
            },
            status_code=200
        )
        
    except Exception as e:
        print(f'❌ Erro ao processar webhook do scheduler: {e}')
        raise HTTPException(status_code=500, detail=str(e))




# ============================================================================
# ROTA DE HEALTH CHECK (Opcional)
# ============================================================================


@app.get('/health')
async def health_check():
    """
    Rota simples para verificar se a app está rodando.
    Útil para monitoramento.
    """
    return {'status': 'ok', 'message': 'Aplicação rodando com sucesso'}
