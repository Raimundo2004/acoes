import os

import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv


load_dotenv()

#CONECTANDO COM O BANCO DE DADOS
url_banco = URL.create(
    "postgresql+psycopg2",
    username= os.environ["DB_USER"],
    password=os.environ["PASSWORD"],
    host=os.environ["DB_HOST"],
    port=5432,
    database="postgres",
)

engine = create_engine(url_banco)

def atualizar():
    #PUXANDO A API
    url = "https://brapi.dev/api/v2/stocks/historical"
    TOKEN = os.environ["BRAPI_TOKEN"]
    hearder = {"Authorization": f"Bearer {TOKEN}"}
    simbolo = ['PETR4', 'VALE3', 'MGLU3','ITUB4'] #Ações que eu quero analisar

    response = requests.request("GET", url, headers=hearder, params={"symbols": ",".join(simbolo),
               "range": "3mo", #Pegar dados no período de 3 anos
               "interval": "1d", #Nesses 3 anos pegou dados de cada dia
               "sortOrder": "asc",
               }, timeout=30, )
    response.raise_for_status()

    resultado = response.json() #Dados em formato Json

    #CRIANDO UMA VARIÁVEL PARA GUARDA OS NOVOS DADOS
    linhas = []
    hoje = datetime.today().strftime('%d/%m/%Y') #Varíavel do dia atual

    #PEGANDO OS DADOS JSON
    for i in resultado['results']:
        data = i.get('data')
        if not data:
            continue
        for dia in data['historicalDataPrice']:
            data_dia = datetime.fromtimestamp(dia['date']).strftime('%d/%m/%Y') #Formatando os dados em Data
            if data_dia != hoje: #Ignora os dados que não for o dia atual
                continue
            #Aplicando dados que for no dia atual
            linhas.append({
                'Simbolo': i['requestedSymbol'],
                'Data': data_dia,
                'Open': dia['open'],
                'High': dia['high'],
                'Low': dia['low'],
                'Close': dia['close'],
            })
    if not linhas: #Se não for publicado ele gera essa informação
        print("Nenhum registro hoje")
        return
    print("Dados recebidos da brapi:", len(linhas))

    with engine.begin() as conn: #Atualiza o banco de dados
        resultado = conn.execute(
            text("""
                INSERT INTO public.hist_moeda ("Simbolo", "Data", "Open", "High", "Low", "Close")
                VALUES (:Simbolo, :Data, :Open, :High, :Low, :Close)
                ON CONFLICT ("Simbolo", "Data") DO UPDATE SET
                    "Open" = EXCLUDED."Open",
                    "High" = EXCLUDED."High",
                    "Low" = EXCLUDED."Low",
                    "Close" = EXCLUDED."Close"
            """),
            linhas,
        )
        print("Linhas afetadas:", resultado.rowcount)

        tabela = pd.DataFrame(linhas)

        print(tabela)

    print("Transação concluída")

atualizar()