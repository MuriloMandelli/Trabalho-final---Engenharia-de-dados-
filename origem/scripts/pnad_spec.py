"""Colunas da PNAD Contínua (microdados trimestrais do IBGE) que viram tabelas do banco de origem.

Cada item: (variável no dicionário do IBGE, tipo, descrição).
  tipo: 'txt' = código/texto, 'int' = inteiro, 'num' = decimal.
No banco, o nome da coluna é a variável em minúsculas (assim dá para conferir no dicionário oficial).
CONFIRA as descrições no dicionário do IBGE antes de usar na documentação.
"""

# 1 registro por domicílio e trimestre
DOMICILIO = [
    ("Ano", "int", "ano de referência"),
    ("Trimestre", "int", "trimestre de referência"),
    ("UF", "txt", "código da unidade da federação"),
    ("Capital", "txt", "município da capital"),
    ("RM_RIDE", "txt", "região metropolitana / RIDE"),
    ("UPA", "txt", "unidade primária de amostragem"),
    ("Estrato", "txt", "estrato de amostragem"),
    ("V1008", "txt", "número de seleção do domicílio"),
    ("V1014", "txt", "painel (grupo de rotação)"),
    ("V1022", "txt", "situação do domicílio (urbana/rural)"),
    ("V1023", "txt", "tipo de área (capital, resto da RM, resto da UF)"),
    ("V2001", "int", "número de pessoas no domicílio"),
]

# 1 registro por pessoa moradora e trimestre
MORADOR = [
    ("V2003", "int", "número de ordem da pessoa no domicílio"),
    ("V2005", "txt", "condição no domicílio"),
    ("V2007", "txt", "sexo"),
    ("V2009", "int", "idade na data de referência"),
    ("V2010", "txt", "cor ou raça"),
    ("V3001", "txt", "sabe ler e escrever"),
    ("V3002", "txt", "frequenta escola"),
    ("V3009A", "txt", "curso mais elevado que frequentou"),
    ("VD3004", "txt", "nível de instrução mais elevado"),
    ("VD3005", "int", "anos de estudo"),
    ("VD4001", "txt", "condição na força de trabalho"),
    ("VD4002", "txt", "condição de ocupação"),
    ("V1027", "num", "peso sem pós-estratificação"),
    ("V1028", "num", "peso com pós-estratificação"),
    ("V1029", "num", "projeção da população"),
]

# 1 registro por pessoa OCUPADA (VD4002 = 1) e trimestre
OCUPACAO = [
    ("V4009", "int", "quantidade de trabalhos"),
    ("V4010", "txt", "código da ocupação do trabalho principal"),
    ("V4012", "txt", "posição na ocupação"),
    ("V4013", "txt", "código da atividade (CNAE-Domiciliar)"),
    ("V4029", "txt", "carteira de trabalho assinada"),
    ("V4032", "txt", "contribui para instituto de previdência"),
    ("V4039", "int", "horas habitualmente trabalhadas no trabalho principal"),
    ("VD4009", "txt", "posição na ocupação e categoria do emprego"),
    ("VD4010", "txt", "grupamento de atividade do trabalho principal"),
    ("VD4011", "txt", "grupamento ocupacional do trabalho principal"),
    ("VD4012", "txt", "contribuição para previdência (derivada)"),
    ("VD4016", "num", "rendimento habitual do trabalho principal"),
    ("VD4017", "num", "rendimento efetivo do trabalho principal"),
    ("VD4019", "num", "rendimento habitual de todos os trabalhos"),
    ("VD4020", "num", "rendimento efetivo de todos os trabalhos"),
    ("VD4031", "int", "horas habituais em todos os trabalhos"),
]

TIPOS_SQL = {"txt": "TEXT", "int": "INTEGER", "num": "NUMERIC"}
