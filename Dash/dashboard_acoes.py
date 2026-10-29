import streamlit as st
import plotly.express as px
import plotly.graph_objects as po
import pandas as pd
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv
import os

load_dotenv()

#CONECTANDO COM O BANCO DE DADOS
@st.cache_resource
def get_engine():
    url_banco = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=5432,
        database="postgres",
    )
    return create_engine(url_banco)


@st.cache_data(ttl=1800, show_spinner="Carregando dados...")
def carregar_hist():
    df = pd.read_sql("SELECT * FROM public.hist_moeda", get_engine())
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df = df.sort_values('Data').reset_index(drop=True)
    df['Ano'] = df['Data'].dt.year
    return df


@st.cache_data(ttl=1800)
def carregar_prev():
    p = pd.read_sql("SELECT * FROM public.prev_moeda", get_engine())
    p['data_dt'] = pd.to_datetime(p['data'], format='%d/%m/%Y')
    return p.sort_values('data_dt').reset_index(drop=True)


df = carregar_hist()
df1 = carregar_prev()


#FILTROS
st.sidebar.title("Filtros")
anos = sorted(df["Ano"].unique().tolist())

ano = st.sidebar.segmented_control(
    "Ano",
    options=anos,
    width="stretch",
)

filtro = df if ano is None else df[df["Ano"] == ano]

data_min = filtro["Data"].min().to_pydatetime()
data_max = filtro["Data"].max().to_pydatetime()

inicio, fim = st.sidebar.slider(
    "Escolha um período",
    min_value=data_min,
    max_value=data_max,
    value=(data_min, data_max),
    format="DD/MM/YYYY",
    key=f"periodo_{ano}",   # reinicia o slider quando o ano muda
)

filtro = filtro[filtro["Data"].between(pd.Timestamp(inicio), pd.Timestamp(fim))]

if filtro.empty:
    st.warning("Não há dados para o período selecionado.")
    st.stop()

#UMA TABELA POR AÇÃO COM FILTRO
vale  = filtro[filtro["Simbolo"] == "VALE3"]
petra = filtro[filtro["Simbolo"] == "PETR4"]
Malu  = filtro[filtro["Simbolo"] == "MGLU3"]
Itau  = filtro[filtro["Simbolo"] == "ITUB4"]

#UMA TABELA POR AÇÃO SEM FILTRO
s_vale  = df[df["Simbolo"] == "VALE3"]
s_petra = df[df["Simbolo"] == "PETR4"]
s_Malu  = df[df["Simbolo"] == "MGLU3"]
s_Itau  = df[df["Simbolo"] == "ITUB4"]


#PEGANDO O VALOR DO DIA ATUAL (SEM FILTRO)
ds_vale = s_vale['Close'].iloc[-1]
ds_petra = s_petra['Close'].iloc[-1]
ds_Malu = s_Malu['Close'].iloc[-1]
ds_Itau = s_Itau['Close'].iloc[-1]

#PEGANDO O VALOR DO DIA ANTERIOR (SEM FILTRO)
da_vale = s_vale['Close'].iloc[-2]
da_petra = s_petra['Close'].iloc[-2]
da_Malu = s_Malu['Close'].iloc[-2]
da_Itau = s_Itau['Close'].iloc[-2]

#PEGANDO A AÇÃO DO PRIMEIRO DIA QUE FOI COLETADO 21/10/2024
i_vale = vale['Close'].iloc[0]
i_petra = petra['Close'].iloc[0]
i_Malu = Malu['Close'].iloc[0]
i_Itau = Itau['Close'].iloc[0]


prev_Vale = df1[df1['simbolo'] == 'VALE3']
prev_Petra = df1[df1['simbolo']=='PETR4']
prev_Malu = df1[df1['simbolo']=='MGLU3']
prev_Itau = df1[df1['simbolo']=='ITUB4']

#PREVISÃO CLOSE
pc_Vale = prev_Vale['close_prev'].iloc[-1]
pc_Petra = prev_Petra['close_prev'].iloc[-1]
pc_Malu = prev_Malu['close_prev'].iloc[-1]
pc_Itau = prev_Itau['close_prev'].iloc[-1]

#VARIAÇÃO PERCENTUAL DO DIA ATUAL PARA O DIA ANTERIOR
va_Vale = (ds_vale - da_vale)/da_vale*100
va_Petra = (ds_petra - da_petra)/da_petra*100
va_Malu = (ds_Malu - da_Malu)/da_Malu*100
va_Itau = (ds_Itau - da_Itau)/da_Itau*100

#VARIAÇÃO PERCENTUAL DO DIA ATUAL PARA O DIA SEGUINTE
var_Vale = (pc_Vale - ds_vale)/ds_vale*100
var_Petra = (pc_Petra - ds_petra)/ds_petra*100
var_Malu = (pc_Malu - ds_Malu)/ds_Malu*100
var_Itau = (pc_Itau - ds_Itau)/ds_Itau*100

#DASHBOARD
st.set_page_config(layout="wide", page_title="Dashboard de Ações Br",page_icon="💰")
st.title("📈 Principais Ações do Brasil")
st.write(f"Última atualização : {df['Data'].iloc[-1].strftime('%d/%m/%Y')}")

#ABAS
aba1, aba2, aba3 = st.tabs(["Detalhe","Geral","Previsão"])

with aba1:
    st.header("Detalhe de cada Ação")
    opcao = st.selectbox("Ações:", df['Simbolo'].unique())
    df_filtrado = filtro[filtro['Simbolo'] == opcao]
    vpi = (df_filtrado['Close'].iloc[-1] - df_filtrado['Close'].iloc[0])/ df_filtrado['Close'].iloc[0] * 100


    st.metric(label=f'Valor e rentabilidade da ação', value=f'R$ {df_filtrado['Close'].iloc[-1]:.2f}',
              delta=f'{vpi:.2f}%', help="Variação entre o início e o fim do período selecionado")
    graf = po.Figure(po.Candlestick(
        x=df_filtrado['Data'],high=df_filtrado['High'],
        open=df_filtrado['Open'], close=df_filtrado['Close'],
        low=df_filtrado['Low'],
    ))
    graf.update_layout(
        height=450,
        xaxis_rangeslider_visible=False,
        yaxis_title="Preço (R$)",
        xaxis_title="Data",
        margin=dict(l=0, r=0, t=10, b=0),
    )

    st.plotly_chart(graf, use_container_width=True)

with aba2:
    st.header("Geral das Ações")
    col1, col2, col3, col4 = st.columns(4)

    #Gráfico de linha da Vale
    col1.metric(label="VALE",value = f'R$ {ds_vale}', delta= f"{va_Vale:.2f}%",
                help=f"Variação em relação ao fechamento de {s_vale['Data'].iloc[-2].strftime('%d/%m/%Y')}")
    graf1 = px.line(s_vale, x="Data", y="Close")
    graf1.update_yaxes(range=[0,90])
    col1.plotly_chart(graf1, use_container_width=True)

    #Gráfico de linha da Petrobrás
    col2.metric(label="PETROBRÁS", value=f'R$ {ds_petra}', delta=f"{va_Petra:.2f}%",
                help=f"Variação em relação ao fechamento de {s_petra['Data'].iloc[-2].strftime('%d/%m/%Y')}")
    graf2 = px.line(s_petra,x="Data",y="Close")
    graf2.update_yaxes(range=[0,90])
    col2.plotly_chart(graf2, use_container_width=True)

    #Gráfico de linha da Magalu
    col3.metric(label="MAGALU", value=f'R$ {ds_Malu}', delta=f"{va_Malu:.2f}%",
                help=f"Variação em relação ao fechamento de {s_Malu['Data'].iloc[-2].strftime('%d/%m/%Y')}")
    graf3 = px.line(s_Malu, x='Data',y="Close")
    graf3.update_yaxes(range=[0,90])
    col3.plotly_chart(graf3, use_container_width=True)

    #Gráfico de linha do Itau
    col4.metric(label="ITAÚ", value=f'R$ {ds_Itau}', delta=f"{va_Itau:.2f}%",
                help=f"Variação em relação ao fechamento de {s_Itau['Data'].iloc[-2].strftime('%d/%m/%Y')}")
    graf4 = px.line(s_Itau, x='Data',y="Close")
    graf4.update_yaxes(range=[0,90])
    col4.plotly_chart(graf4, use_container_width=True)

with aba3:
    st.header(f"Previsão para {df1['data'].iloc[-1]}")
    col1, col2, col3,col4 = st.columns(4)

    #Pregão da Vale
    col1.metric(label="VALE", value=f'R$ {pc_Vale:.2f}' , delta=f'{var_Vale:.2f}%')
    graf1 = po.Figure(po.Candlestick(
        x=prev_Vale['data'].iloc[[-1]],
        open=prev_Vale['open_prev'].iloc[[-1]],
        high=prev_Vale['high_prev'].iloc[[-1]],
        low=prev_Vale['low_prev'].iloc[[-1]],
        close=prev_Vale['close_prev'].iloc[[-1]],
    ))
    graf1.update_xaxes(showgrid=False,zeroline=False,showline=False)
    graf1.update_yaxes(showgrid=False, zeroline=False, showline=False)
    graf1.update_layout(
        height=450,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    col1.plotly_chart(graf1, use_container_width=True)

    #Pregão da Petra
    col2.metric(label='PETROBRÁS', value=f'R$ {pc_Petra:.2f}', delta=f'{var_Petra:.2f}%')
    graf2 = po.Figure(po.Candlestick(
        x=prev_Petra['data'].iloc[[-1]],
        open=prev_Petra['open_prev'].iloc[[-1]],
        high=prev_Petra['high_prev'].iloc[[-1]],
        low=prev_Petra['low_prev'].iloc[[-1]],
        close=prev_Petra['close_prev'].iloc[[-1]],
    ))
    graf2.update_xaxes(showgrid=False,zeroline=False,showline=False)
    graf2.update_yaxes(showgrid=False, zeroline=False, showline=False)
    graf2.update_layout(
        height=450,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    col2.plotly_chart(graf2, use_container_width=True)

    #Pregão da Malu
    col3.metric(label='MAGALU', value=f'R$ {pc_Malu:.2f}', delta=f'{var_Malu:.2f}%')
    graf3 = po.Figure(po.Candlestick(
        x=prev_Malu['data'].iloc[[-1]],
        open=prev_Malu['open_prev'].iloc[[-1]],
        high=prev_Malu['high_prev'].iloc[[-1]],
        low=prev_Malu['low_prev'].iloc[[-1]],
        close=prev_Malu['close_prev'].iloc[[-1]],
    ))
    graf3.update_layout(
        height=450,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    graf3.update_xaxes(showgrid=False,zeroline=False,showline=False)
    graf3.update_yaxes(showgrid=False, zeroline=False, showline=False)
    col3.plotly_chart(graf3, use_container_width=True)

    #Pregão do Itaú
    col4.metric(label='ITAÚ', value=f'R$ {pc_Itau:.2f}', delta=f'{var_Itau:.2f}%')
    graf4 = po.Figure(po.Candlestick(
        x=prev_Itau['data'].iloc[[-1]],
        open=prev_Itau['open_prev'].iloc[[-1]],
        high=prev_Itau['high_prev'].iloc[[-1]],
        low=prev_Itau['low_prev'].iloc[[-1]],
        close=prev_Itau['close_prev'].iloc[[-1]],
    ))
    graf4.update_xaxes(showgrid=False,zeroline=False,showline=False)
    graf4.update_yaxes(showgrid=False, zeroline=False, showline=False)
    graf4.update_layout(
        height=450,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    graf4.update_yaxes(range=[10,60])
    col4.plotly_chart(graf4, use_container_width=True)
