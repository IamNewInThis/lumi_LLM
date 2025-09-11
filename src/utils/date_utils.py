# src/utils/date_utils.py
from datetime import date, datetime

def calcular_edad(birthdate_str: str) -> int:
    birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def calcular_meses(birthdate_str: str) -> int:
    birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
    today = date.today()
    return (today.year - birthdate.year) * 12 + (today.month - birthdate.month) - (today.day < birthdate.day)