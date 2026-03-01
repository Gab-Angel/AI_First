from contextlib import asynccontextmanager
from src.db.tables import create_tables
from src.db.checkpointer import setup_checkpointer
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from src.evo.client import EvolutionAPI
from src.agent.audio_transcription import audio_transcription
from src.db.crud import PostgreSQL
from src.redis.buffer import adicionar_ao_buffer, iniciar_ouvinte_background
from src.redis.rq import enqueue_agent_processing


async def processar_mensagens_agrupadas(numero: str, texto_final: str):
    try:
        print(f'📦 Buffer expirado para: {numero}')
        print(f'💬 Texto agrupado: {texto_final}')
        enqueue_agent_processing(numero, texto_final)

    except Exception as e:
        print(f'❌ Erro ao enfileirar processamento para {numero}: {e}\n')


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('🚀 Inicializando aplicação...')

    create_tables()
    print("🟢 Tabelas do sistema prontas!")

    setup_checkpointer()
    print("🟢 Tabelas do checkpointer prontas!")

    iniciar_ouvinte_background(processar_mensagens_agrupadas)
    print('✅ Sistema de buffer pronto!\n')

    yield

    print('🛑 Encerrando aplicação...')


app = FastAPI(lifespan=lifespan)


@app.post('/webhook')
async def webhook(request: Request):
    try:
        data = await request.json()
        messageType = data['data'].get('messageType')

        key = data['data'].get('key', {})
        from_me = key.get('fromMe', False)

        remoteJid = key.get('remoteJid')
        number = remoteJid.split('@')[0]

        if data:
            if messageType == 'conversation':
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
                message = None

            if from_me:
                print('🤖 Mensagem enviada pela IA/Humano. Salvando e ignorando fluxo.')
                PostgreSQL.save_message(
                    session_id=number,
                    sender='human',
                    message={'type': 'ai', 'content': message}
                )
                return JSONResponse(content={'status': 'mensagem da IA salva'}, status_code=200)

            print(f'📲 Mensagem de: {number}')
            print(f'💬 Conteúdo: {message}')

            user = PostgreSQL.get_user_by_number(number)

            if user and user.get("require_human") is True:
                print(f'🚫 IA bloqueada para {number} (humano no controle)')
                PostgreSQL.save_message(
                    session_id=number,
                    sender='user',
                    message={'type': 'user', 'content': message}
                )
                return JSONResponse(content={'status': 'encaminhado_para_humano'}, status_code=200)

            adicionar_ao_buffer(number, message)
            print(f'➕ Mensagem adicionada ao buffer para {number}\n')

            return JSONResponse(content={'status': 'mensagem adicionada ao buffer'}, status_code=200)

        else:
            print('⚠️ Payload do webhook não continha os dados esperados.')
            return JSONResponse(content={'status': 'payload invalido'}, status_code=400)

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

        numero = payload.get('numero')
        mensagem = payload.get('mensagem')

        if not numero or not mensagem:
            print('❌ Payload inválido: número ou mensagem ausente')
            raise HTTPException(status_code=400, detail='Número e mensagem são obrigatórios')

        print(f'📱 Número: {numero}')
        print(f'💬 Mensagem: {mensagem}')

        evo = EvolutionAPI()
        sender_message = evo.sender_text(number=numero, text=mensagem)

        if sender_message:
            message_payload = {'type': 'ai', 'content': mensagem}
            PostgreSQL.save_message(session_id=numero, message=message_payload)
            print('✅  Mensagem de Lembrete Salva no Banco')

        print(f'✅ Mensagem enviada com sucesso para {numero}!')
        print(f'{"="*60}\n')

        return JSONResponse(content={'status': 'enviado', 'numero': numero}, status_code=200)

    except Exception as e:
        print(f'❌ Erro ao processar webhook do scheduler: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/health')
async def health_check():
    return {'status': 'ok', 'message': 'Aplicação rodando com sucesso'}