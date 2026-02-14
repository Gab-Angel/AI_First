import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Autentica e cria o serviço do Google Calendar"""
        import json
        
        creds = None
        
        # 1. Tenta ler do env (produção)
        token_json_str = os.getenv('GOOGLE_CALENDAR_TOKEN_JSON')
        if token_json_str:
            try:
                token_data = json.loads(token_json_str)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except json.JSONDecodeError as e:
                print(f"⚠️ Erro ao parsear GOOGLE_CALENDAR_TOKEN_JSON: {e}")
        
        # 2. Fallback para arquivo local (desenvolvimento)
        if not creds and os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # 3. Valida e renova se necessário
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                print("✅ Token renovado com sucesso")
            else:
                # OAuth flow (só funciona local com credentials.json)
                if os.path.exists(self.credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                    # Salva localmente para próximas vezes
                    with open(self.token_path, "w") as token:
                        token.write(creds.to_json())
                else:
                    raise Exception(
                        "❌ Não foi possível autenticar. "
                        "Configure GOOGLE_CALENDAR_TOKEN_JSON no env "
                        "ou forneça credentials.json localmente."
                    )
        
        self.service = build("calendar", "v3", credentials=creds)
    
    def verificar(self, data_inicio: str, data_fim: str, calendar_id: str):
        """
        Verifica eventos ocupados na agenda
        
        Args:
            data_inicio: Data/hora início ISO 8601 (ex: "2026-01-10T08:00:00-03:00")
            data_fim: Data/hora fim ISO 8601
            calendar_id: ID da agenda (default: "primary")
        
        Returns:
            list: Lista de eventos ocupados com id, summary, start, end
        """
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=data_inicio,
                timeMax=data_fim,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            
            return [{
                "id": event["id"],
                "summary": event.get("summary", "Sem título"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date"))
            } for event in events]
            
        except HttpError as error:
            raise Exception(f"Erro ao verificar agenda: {error}")
    
    def adicionar(self, summary, start_time, end_time, calendar_id: str, description=""):
        """
        Adiciona evento na agenda
        
        Args:
            summary: Título do evento
            start_time: Data/hora início ISO 8601
            end_time: Data/hora fim ISO 8601
            calendar_id: ID da agenda (default: "primary")
            description: Descrição do evento
        
        Returns:
            dict: Evento criado com id, summary, start, end, link
        """
        try:
            event = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_time, "timeZone": "America/Sao_Paulo"},
                "end": {"dateTime": end_time, "timeZone": "America/Sao_Paulo"}
            }
            
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            return {
                "id": created_event["id"],
                "summary": created_event["summary"],
                "start": created_event["start"]["dateTime"],
                "end": created_event["end"]["dateTime"],
                "link": created_event.get("htmlLink")
            }
            
        except HttpError as error:
            raise Exception(f"Erro ao adicionar evento: {error}")
    
    def deletar(self, event_id, calendar_id: str):
        """
        Deleta evento da agenda
        
        Args:
            event_id: ID do evento a ser deletado
            calendar_id: ID da agenda (default: "primary")
        
        Returns:
            bool: True se deletado com sucesso
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return True
            
        except HttpError as error:
            raise Exception(f"Erro ao deletar evento: {error}")