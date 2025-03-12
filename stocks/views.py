from django.shortcuts import render
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from django.urls import path
from django.http import HttpResponse
import requests
import matplotlib
matplotlib.use("Agg")

def fetch_stock_data(tickers, start_date, end_date):
    
    tickers = [ticker.strip() for ticker in tickers if ticker.strip()]  # Pega os tickers selecionados e organiza-os em lista
    stock = yf.download(tickers, start=start_date, end=end_date, group_by="ticker") # Procura os tickers selecionados no Yahoo Finance

    valid_tickers = [t for t in tickers if "." in t]  # O Yahoo Finance usa "."//SA para ações brasileiras, sendo fácil de identificá-las
    if not valid_tickers:
        print("Nenhum ticker válido foi fornecido.")
        return pd.DataFrame()

    if stock.empty:
        print(f"Nenhum dado encontrado para {tickers}.")
        return pd.DataFrame()

    '''Utilizados somente para validação e Debug no Terminal do Visual Studio'''
    # print(f"Estrutura do DataFrame para {tickers}:\n", stock.head())
    # print("Colunas disponíveis:", stock.columns)

    closing_prices = pd.DataFrame()

    for ticker in tickers: # Validação para a procura do preço de fechamento de cada dia
        if isinstance(stock.columns, pd.MultiIndex):
            try:
                closing_prices[ticker] = stock[ticker]['Close']
            except KeyError:
                print(f"'Close' não encontrado para {ticker}.")
                continue
        else:
            if "Close" in stock.columns:
                closing_prices[ticker] = stock["Close"]
            else:
                print(f"'Close' não encontrado na estrutura real: {stock.columns}")
                return pd.DataFrame()

    closing_prices.index = pd.to_datetime(closing_prices.index)
    closing_prices.columns = [ticker.strip() for ticker in closing_prices.columns]  # Separando cada ticker com suas colunas

    '''Utilizados somente para validação e Debug no Terminal do Visual Studio'''
    # print(f"Dados após ajuste: {closing_prices.head()}")
    # print("\n----------------------------------------------------------------")
    # print(tickers)
    # print("----------------------------------------------------------------\n")

    return closing_prices # Retorna os valores de fechamento das ações

def calculate_return(df): # Função que calcula a rentabilidade de cada ação segundo fórmula descrita no documento enviado

    if df.empty: # Validação para o DataFrame
        print("DataFrame vazio, não é possível calcular a rentabilidade.")
        return df

    df.index = pd.to_datetime(df.index) # Garantindo que o índice está no formato de datas

    if len(df) < 2: # Se houver apenas um dia, não há rentabilidade a calcular
        print("Apenas um ponto de dados disponível. Não há variação para calcular rentabilidade.")
        return df  # Retorna o DataFrame original para evitar divisão por zero
    
    return ((df - df.iloc[0]) / df.iloc[0]) * 100 # Calcula a rentabilidade acumulada para cada coluna (ação)

def plot_stock_returns(df): # Função que retorna um gráfico com a rentabilidade de cada ação durante o período selecionado

    if df.empty:
        print("DataFrame vazio, não é possível gerar gráfico.")
        return ""

    # print("Gerando gráfico. Estrutura dos dados:\n", df.head())

    plt.figure(figsize=(10, 5)) # O gráfico será gerado no backend e enviado para o front em formato de imagem, aqui definimos seu tamanho

    for column in df.columns: # Marca um ponto "o", para cada dia indicado nas colunas
        plt.plot(df.index, df[column], label=column, marker='o')

    '''Montagem do gráfico'''
    plt.legend()
    plt.xlabel("Data")
    plt.ylabel("Rentabilidade (%)")
    plt.title("Comparação de Rentabilidade Acumulada")

    plt.xticks(rotation=45)
    
    plt.tight_layout() # Evita que o gráfico fique cortado no front

    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()

    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()

    return image_base64



def export_csv(request): # Função que retorna um arquivo em formato .csv com a rentabilidade de cada ação durante o período selecionado

    tickers = request.GET.getlist("tickers")  # Pegamos a seleção do usuário

    # print(f"Tickers brutos recebidos: {tickers}") Verificação

    '''Ajuste dos tickers, que são recebidos com "," entre cada letra'''
    tickers_cleaned = []
    for ticker in tickers:
        raw_tickers = ticker.split(",,,")  # Divide onde houver erro de múltiplas vírgulas (que ocorre entre cada ticker)
        tickers_cleaned.extend(["".join(t.split(",")) for t in raw_tickers])

     # print(f"Tickers corrigidos: {tickers_cleaned}") Verificação

    start_date = request.GET.get("start_date") # Pegamos a seleção do usuário
    end_date = request.GET.get("end_date") # Pegamos a seleção do usuário

    if tickers_cleaned and start_date and end_date: # Chama a função "fetch_stock_data", e pega novamente os dados de cada ticker no Yahoo Finance
        df = fetch_stock_data(tickers_cleaned, start_date, end_date)
        
        if df.empty:  # Validação
            return HttpResponse("Erro: Nenhum dado disponível para exportação.", status=400)

        returns_df = calculate_return(df).round(2)  # Rentabilidade arredondada para duas casas decimais

        # Criar um DataFrame formatado para exportação
        export_df_list = []  

        '''Criação e ajuste da tabela montada dentro 5do arquivo (aberto em excel)'''
        for ticker in tickers_cleaned:
            if ticker in df.columns:
                temp_df = pd.DataFrame({
                    "Data": df.index.strftime("%Y-%m-%d"),
                    "Ticker da Acao": ticker,
                    "Preco de Fechamento": df[ticker].round(2),
                    "Rentabilidade (%)": returns_df.get(ticker, pd.Series([None] * len(df), index=df.index)).round(2)  # Evita KeyError
                })
                export_df_list.append(temp_df)

        if export_df_list:
            export_df = pd.concat(export_df_list)
        else:
            return HttpResponse("Erro: Dados insuficientes para exportação.", status=400)

        response = HttpResponse(content_type='text/csv') # Criando a resposta HTTP com csv para os arquivos e urls já definidos
        response['Content-Disposition'] = 'attachment; filename="stock_data.csv"'

        export_df.to_csv(path_or_buf=response, index=False, encoding="utf-8", sep=";")

        return response

    return HttpResponse("Erro ao gerar CSV", status=400) # Caso ocorra erro nessa parte do programa

def stock_selection_view(request): # Função que retorna as ações da B3 listadas no Yahoo Finance para que o usuários possa selecioná-las na página "forms.html"
    tickers = [
        "ALOS3.SA", "ALPA4.SA", "ABEV3.SA", "ASAI3.SA", "AZUL4.SA", "B3SA3.SA", "BBSE3.SA", "BBDC3.SA",
        "BBDC4.SA", "BRAP4.SA", "BBAS3.SA", "BRKM5.SA", "BRFS3.SA", "BPAC11.SA", "MRFG3.SA", "BEEF3.SA", "MRVE3.SA", "MULT3.SA",
        "PCAR3.SA", "PETR3.SA", "PETR4.SA", "RECV3.SA", "PRIO3.SA", "PETZ3.SA", "RADL3.SA", "RAIZ4.SA", "RDOR3.SA", "RAIL3.SA",
        "SBSP3.SA", "SANB11.SA", "SMTO3.SA", "CSNA3.SA", "SLCE3.SA", "SUZB3.SA", "TAEE11.SA", "VIVT3.SA", "TIMS3.SA", "TOTS3.SA",
        "UGPA3.SA", "USIM5.SA", "VALE3.SA", "VAMO3.SA", "VBBR3.SA", "WEGE3.SA", "YDUQ3.SA", "CRFB3.SA", "BHIA3.SA",
        "CCRO3.SA", "CMIG4.SA", "COGN3.SA", "CPLE6.SA", "CSAN3.SA", "CPFE3.SA", "CMIN3.SA", "CVCB3.SA", "CYRE3.SA",
        "DXCO3.SA", "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENGI11.SA", "ENEV3.SA", "EGIE3.SA", "EQTL3.SA", "EZTC3.SA", "FLRY3.SA",
        "GGBR4.SA", "GOAU4.SA", "NTCO3.SA", "HAPV3.SA", "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", "ITSA4.SA", "ITUB4.SA",
        "JBSS3.SA", "KLBN11.SA", "RENT3.SA", "LREN3.SA", "LWSA3.SA", "MGLU3.SA"
    ]

    return render(request, "stocks/form.html", {"tickers": tickers})


def stock_analysis_view(request):  # Função que renderiza a análise da rentabilidade das ações (em analysis.html)"

    '''Pegando a seleção do usuário'''
    if request.method == "GET" and "tickers" in request.GET:
        tickers = request.GET.getlist("tickers") 
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        '''Validando dados e chamando a função "fetch_stock_data"'''
        if tickers and start_date and end_date:
            try:
                df = fetch_stock_data(tickers, start_date, end_date)

                if df.empty:
                    return HttpResponse("Nenhum dado disponível para os tickers fornecidos.", status=400)

                returns_df = calculate_return(df)

                if returns_df.empty:
                    return HttpResponse("Erro: Nenhuma rentabilidade calculada.", status=400)

                graph = plot_stock_returns(returns_df) # Instanciando o gráfico com a função "plot_stock_returns"

                context = {
                    "graph": graph,
                }

                return render(request, "stocks/analysis.html", context) # Enviando dados para a página analysis.html

            except ValueError as e:
                return HttpResponse(f"Erro: {str(e)}", status=400)