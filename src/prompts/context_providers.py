from datetime import datetime, timedelta

class ContextProvider:
    @staticmethod
    def context_datetime(state):
        DIAS_PT = {
            "Monday": "segunda-feira",
            "Tuesday": "terça-feira",
            "Wednesday": "quarta-feira",
            "Thursday": "quinta-feira",
            "Friday": "sexta-feira",
            "Saturday": "sábado",
            "Sunday": "domingo",
        }

        now_dt = datetime.now()
        day_en = now_dt.strftime("%A")
        day_pt = DIAS_PT.get(day_en, day_en)

        now = now_dt.strftime("%Y-%m-%d %H:%M:%S") + f" | {day_pt}"

        return f"DATA/HORA ATUAL: {now}"


    @staticmethod
    def context_user_number(state):
        numero = state["number"]
        return f"IMPORTANTE: O número do usuário é {numero}."


    @staticmethod
    def context_calendario(state):
        hoje = datetime.now()
        dias_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']

        calendario = []
        for i in range(31):
            data = hoje + timedelta(days=i)
            dia_semana = dias_semana[data.weekday()]
            calendario.append(f"{data.strftime('%d/%m')} ({dia_semana})")

        calendario_ref = " | ".join(calendario)

        return (
            f"CALENDÁRIO de 31 dias: {calendario_ref}\n"
            f"IMPORTANTE: Use o calendário acima para identificar dias da semana."
        )

