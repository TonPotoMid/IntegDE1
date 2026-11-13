"""Valeurs attendues calculées À LA MAIN à partir du jeu de données déterministe."""
from decimal import Decimal as D

A = "FR7630006000011234567890189"  # BNP Paribas
F = "FR7630004000031234567890143"  # BNP Paribas
B = "DE89370400440532013000"       # Deutsche Bank
C = "ES9121000418450200051332"     # CaixaBank
DD = "IT60X0542811101000000123456"  # UniCredit
E = "FR1420041010050500013M02606"  # La Banque Postale

TOTAL_TRANSACTIONS = 18
TOTAL_AMOUNT = D("61476.50")
FLAGGED_IDS = {"T002", "T007", "T009", "T014", "T018"}  # T004 = 5000.00 pile -> non flaggé

SENT_BY_IBAN = {
    A: D("22649.99"),
    B: D("16740.25"),
    C: D("17800.51"),
    DD: D("1145.75"),
    E: D("980.00"),
    F: D("2160.00"),
}
SENT_BY_BANK = {
    "BNP Paribas": D("24809.99"),
    "Deutsche Bank": D("16740.25"),
    "CaixaBank": D("17800.51"),
    "UniCredit": D("1145.75"),
    "La Banque Postale": D("980.00"),
}
RECEIVED_BY_IBAN = {
    A: D("5300.50"),
    B: D("4375.74"),
    C: D("22560.00"),
    DD: D("18140.25"),
    E: D("11100.01"),
}
