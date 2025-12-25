import re
import hashlib

def validate_phone(phone):
    """Валидация номера телефона РФ"""
    pattern = r'^\+7\s\(\d{3}\)\s\d{3}-\d{2}-\d{2}$'
    return re.match(pattern, phone) is not None

def validate_passport_series(series):
    """Валидация серии паспорта (4 цифры)"""
    return len(str(series)) == 4 and str(series).isdigit()

def validate_passport_number(number):
    """Валидация номера паспорта (6 цифр)"""
    return len(str(number)) == 6 and str(number).isdigit()

def validate_password(password):
    """Валидация пароля: минимум 8 символов, буквы и цифры"""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit

def validate_organization(number):
    """Валидация номера организации (5-15 цифр)"""
    cleaned = re.sub(r'\D', '', str(number))
    return 5 <= len(cleaned) <= 15

def hash_password(password):
    """Хэширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()