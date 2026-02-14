import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

# Configurações
BASE_URL_SCHEDULER = os.getenv("BASE_URL_SCHEDULER")  
API_TOKEN_SCHEDULER = os.getenv("API_TOKEN_SCHEDULER") 
WEBHOOK_URL_SCHEDULER = os.getenv("WEBHOOK_URL_SCHEDULER")  
TIME_SCHEDULER = 2

headers = {
    "Authorization": f"Bearer {API_TOKEN_SCHEDULER}",
    "Content-Type": "application/json"
}


def create_scheduler_message(
    event_id_scheduler: str,
    numero: str,
    schedule_time: str
    )-> str: 

    print("\n📝 Criando Lembrete ")

    
    schedule = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
    send_date = schedule - timedelta(hours=TIME_SCHEDULER)
    send_date_iso = send_date.isoformat().replace('+00:00', 'Z')

    payload = {
        "id": event_id_scheduler,
        "scheduleTo": send_date_iso,
        "payload": {
            "mensagem": f"Olá, passando aqui para lembrar da nossa consulta.\nSe houver qualquer imprevisto entre em contato com o doutor(a) responsável pela sua consulta.\nTenha um ótimo dia!!",
            "numero": numero
        },
        "webhookUrl": WEBHOOK_URL_SCHEDULER
    }

    try:

        response = requests.post(
            f"{BASE_URL_SCHEDULER}/messages",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            return ("Lembrete Salvo com Sucesso!!!")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None
    

def delete_scheduler_message(event_id_scheduler: str):

    print(f"\n🗑️  Deletando Lembrete  (ID: {event_id_scheduler})...")
    
    if not event_id_scheduler:
        print("⚠️ Nenhum message_id fornecido")
        return False
    
    try:
        response = requests.delete(
            f"{BASE_URL_SCHEDULER}/messages/{event_id_scheduler}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            return ("Lembrete Deletado com Sucesso!!!")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao deletar mensagem: {e}")
        return False
    




if __name__ == "__main__":
    """schedule_time = (datetime.utcnow() + timedelta(seconds=10)).isoformat() + "Z"
    teste = create_scheduler_message(event_id_scheduler="12345",numero="557998760230", schedule_time=schedule_time)
    print(teste)"""

    teste = delete_scheduler_message(event_id_scheduler="voa0fcrksbt82cplarcpqlpd9s")
