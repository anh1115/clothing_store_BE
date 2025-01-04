import unicodedata
import re

def remove_accents(input_str):
    """
    Loại bỏ dấu từ một chuỗi Unicode.
    """
    nfkd_str = unicodedata.normalize('NFKD', input_str)
    return re.sub(r'[\u0300-\u036f]', '', nfkd_str)
