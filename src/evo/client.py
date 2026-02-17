import os
from src.db.crud import PostgreSQL

import requests
from dotenv import load_dotenv

load_dotenv()


# CONEXÃO COM EVOLUTION
base_url_evo = os.getenv('BASE_URL_EVO')
instance_token = os.getenv('API_KEY_EVO')
instance_name = os.getenv('INSTANCE_NAME')

url_sendText = f'{base_url_evo}/message/sendText/{instance_name}'
url_sendMedia = f'{base_url_evo}/message/sendMedia/{instance_name}'
headers = {'Content-Type': 'application/json', 'apikey': instance_token}


class EvolutionAPI:
    def __init__(self):
        self.base_url_evo = base_url_evo
        self.instance_name = instance_name
        self.headers = headers

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f'{self.base_url_evo}{endpoint}/{self.instance_name}'
        response = requests.post(url=url, headers=self.headers, json=payload)

        response.raise_for_status()
        return response.json()

    def sender_text(self, number: str, text: str) -> list[dict]:
        
        # Remove apenas espaços em branco excessivos, mantém \n
        texto = text.strip()
        
        # Divide por parágrafos (blocos separados por \n\n)
        paragrafos = [p.strip() for p in texto.split('\n\n') if p.strip()]
        
        responses = []
        
        for paragrafo in paragrafos:
            # Se parágrafo > 300 chars, quebra em frases
            if len(paragrafo) > 300:
                # Split inteligente: só quebra após ., !, ? seguidos de espaço
                import re
                frases = re.split(r'(?<=[.!?])\s+', paragrafo)
                
                for frase in frases:
                    if not frase.strip():
                        continue
                        
                    payload = {
                        'number': number,
                        'text': frase.strip(),
                        'delay': min(len(frase) * 30, 3000),  # Simula digitação (max 3s)
                        'presence': 'composing',
                    }
                    
                    response = self._post(endpoint='/message/sendText', payload=payload)
                    responses.append(response)
            else:
                # Parágrafo curto: envia inteiro
                payload = {
                    'number': number,
                    'text': paragrafo,
                    'delay': min(len(paragrafo) * 30, 3000),
                    'presence': 'composing',
                }
                
                response = self._post(endpoint='/message/sendText', payload=payload)
                responses.append(response)
        
        return responses

    def sender_file(
        self,
        numero: str,
        media_type: str,
        file_name: str,
        media: str,
        caption: str = '',
    ) -> dict:

        payload = {
            'number': numero,
            'mediatype': media_type,
            'fileName': file_name,
            'media': media,
            'caption': caption,
            'delay': 2000,
            'presence': 'composing',
        }

        return self._post(endpoint='/message/sendMedia', payload=payload)

    # ====================================================
    def notificar_admin_agendamento(self, paciente_numero: str, procedimento: str, descricao: str, event_id: str, data_inicio: str, data_fim: str):
        
        admin_rosevania = os.getenv('ADM_NUMBER_ROSEVANIA')
        admin_felipe = os.getenv('ADM_NUMBER_FELIPE')

        if not admin_rosevania and admin_felipe:
            print("⚠️ ADMs não configurado no .env")
            return
        
        # Busca dados do paciente
        paciente = PostgreSQL.get_user_by_number(paciente_numero)
        
        if paciente:
            nome = paciente.get('nome_completo', 'Nome não cadastrado')
            convenio = paciente['observacoes']['convenio_tipo']
            documento = paciente['observacoes']['documento']
        else:
            nome = 'Não cadastrado'

        if documento == "cpf_informado":
            cpf = paciente.get('cpf')
            documento = f'CPF -> {cpf}'

        elif documento == 'carteirinha_enviada':
            documento = "Paciente enviou a carteirinha"

        else:
            documento = 'Sem documento'

        # Extrai data e hora
        data = data_inicio[:10]  # YYYY-MM-DD
        hora_inicio = data_inicio[11:16]  # HH:MM
        hora_fim = data_fim[11:16]  # HH:MM
        
        # Formata mensagem
        mensagem = f"""🔔 *Novo Agendamento Realizado*

    👤 Paciente: {nome}
    📞 Telefone: {paciente_numero}
    📅 Data: {data}
    🕐 Horário: {hora_inicio} às {hora_fim}
    Convênio: {convenio}
    Documento: {documento}
    Procedimento: {procedimento}
    Observações: {descricao}

    Verifique a agenda ou entre em contato."""
        
        # Envia notificação
        try:

            get_event = PostgreSQL.get_responsavel_event(event_id=event_id)
            responsavel = get_event['dr_responsavel']

            if responsavel == "Rosevânia":
                admin_numero = admin_rosevania
            else:
                admin_numero = admin_felipe

            payload = {
                'number': admin_numero,
                'text': mensagem,
                'delay': 2000,
                'presence': 'composing',
            }

            response = self._post(
                endpoint='/message/sendText', payload=payload
            )
            
        
            print(f"✅ Admin {admin_numero} notificado sobre agendamento")
        except Exception as e:
            print(f"❌ Erro ao notificar admin: {e}")
    # ====================================================

    def notify_human(self, phone_number: str, reason: str):

        user = PostgreSQL.get_user_by_number(number=phone_number)
        nome = user.get('nome_completo', 'Nome não cadastrado')

        mensagem = f"""🔔 *Paciente precisando de atendimento*

        👤 Paciente: {nome}
        📞 Telefone: {phone_number}
        🗣️ Motivo: {reason}

        Entre em contato."""

        admin_numero = os.getenv('ADM_NUMBER')

        try:
            payload = {
                    'number': admin_numero,
                    'text': mensagem,
                    'delay': 2000,
                    'presence': 'composing',
                }

            response = self._post(
                endpoint='/message/sendText', payload=payload
            )

            print(f"✅ Admin {admin_numero} notificado sobre agendamento")
        except Exception as e:
            print(f"❌ Erro ao notificar admin: {e}")       

