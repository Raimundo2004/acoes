import pandas as pd
import joblib
from dotenv import load_dotenv
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import create_engine, URL, text
import os
from datetime import datetime, timedelta

pacote = joblib.load("predict.joblib")


def carregar():
    load_dotenv()

    url_banco = URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["PASSWORD"],
        host=os.environ["DB_HOST"],
        port=5432,
        database="postgres",
    )

    supabase = create_engine(url_banco)
    return pd.read_sql("SELECT * FROM public.hist_moeda", supabase)


def verificar(df):
    hoje = pd.Timestamp.now(tz='America/Sao_Paulo').normalize().tz_localize(None)
    if hoje.dayofweek >= 5:
        print("Fim de semana sem valor, nada a prever")
        return df.iloc[0:0]
    dp = df[df["Data"]==hoje]
    if dp.empty:
        print(f"Sem dados de {hoje:%d/%m/%Y} (feriado ou coleta não rodou). "
              f"Última data no banco: {df['Data'].max():%d/%m/%Y}")
    return dp

def featurizar_prev(df):
    dt = df.copy()
    encoder = pacote['encoder']
    dt = dt[dt['Simbolo'].isin(encoder.classes_)]
    dt['Simbolo_txt'] = dt['Simbolo']
    dt['Simbolo'] = encoder.fit_transform(dt['Simbolo_txt'])
    dt['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    dt = dt.sort_values(['Simbolo', 'Data']).reset_index(drop=True)
    dt['ret_Close'] = dt['Close'].pct_change()
    dt['ret_Open'] = dt['Open'].pct_change()
    for i in [1, 2, 3, 4, 5]:
        dt[f"ret_lag_{i}"] = dt["ret_Close"].shift(i)

    dt['sma_5'] = dt['Close'].rolling(5).mean()
    dt['sma_20'] = dt['Close'].rolling(20).mean()
    dt['vol_20'] = dt['Close'].rolling(20).std()
    dt["range"] = (dt["High"] - df["Low"]) / df['Close']
    dt['Month'] = dt['Data'].dt.month
    dt['Day'] = dt['Data'].dt.day
    dt['Year'] = dt['Data'].dt.year
    dt['DayOfWeek'] = dt['Data'].dt.day_of_week
    return dt

def apagar_data(df):
    dt = df.copy()
    return dt.drop(columns=['Data'])

def prev(df):
    dp = df.copy()
    modelo, scaler = pacote['modelo'], pacote['scaler']
    prev = modelo.predict(scaler.transform(dp[pacote['features']]))
    col = ["open_Prev", "high_Prev", "low_Prev", "close_Prev"]
    tb = pd.DataFrame(prev).copy()
    tb.columns = col
    return tb

def concat(df,prev):
    dp = df.copy()
    prd = prev.copy()
    return pd.concat([dp.reset_index(drop=True),prd.reset_index(drop=True)], axis=1)


def atualizar(df):
    encoder = pacote['encoder']
    amanha = pd.Timestamp.now(tz='America/Sao_Paulo').normalize().tz_localize(None) + pd.offsets.BDay(1)

    df = df.copy()
    df['Simbolo'] = encoder.inverse_transform(df['Simbolo'].astype(int))
    df['data_Prev'] = amanha.strftime('%d/%m/%Y')

    colunas = ['Simbolo', 'data_Prev', 'open_Prev', 'high_Prev', 'low_Prev', 'close_Prev']
    registros = df[colunas].to_dict('records')

    load_dotenv()
    url_banco = URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["PASSWORD"],
        host=os.environ["DB_HOST"],
        port=5432,
        database="postgres",
    )
    supabase = create_engine(url_banco)

    with supabase.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO public.prev_moeda
                    (simbolo, data, open_prev, high_prev, low_prev, close_prev)
                VALUES
                    (:Simbolo, :data_Prev, :open_Prev, :high_Prev, :low_Prev, :close_Prev)
                ON CONFLICT (simbolo, data)
                DO UPDATE SET
                    open_prev  = EXCLUDED.open_prev,
                    high_prev  = EXCLUDED.high_prev,
                    low_prev   = EXCLUDED.low_prev,
                    close_prev = EXCLUDED.close_prev
             """),
            registros,
        )
    print(f"{len(registros)} previsões gravadas para {amanha:%d/%m/%Y}")

def main():
    df = carregar()
    print('====================================== DADOS CARREGADO ======================================')
    df = featurizar_prev(df)
    df = verificar(df)
    if df.empty:
        return None
    print(f"====================================== DADOS DO DIA ======================================\n{df}")
    df = apagar_data(df)
    prd = prev(df)
    resulp = concat(df, prd)
    df = atualizar(resulp)
    print(df)
    return df

if __name__ == "__main__":
    main()