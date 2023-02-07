# -*- coding: utf-8 -*-"""Created on Mon Jan 30 19:50:15 2023@author: Tania"""# python3 -m venv venv/ import pandas as pdimport pathlibimport globfrom os import listdirfrom os.path import isfile, joinimport numpy as npimport pandas_datareader.data as webfrom scipy.optimize import minimizeimport yfinance as yfdef import_files(path):    """ This function imports all files in folder given the folder path.    It ignores the first two rows and sorts the Tickers in alphabetical order."""    files = list(glob.glob(path))    all_files = {}    for i in files:        data = pd.read_csv(i, skiprows=2).iloc[:-1 , :]        all_files[i[14:22]] = data[['Ticker', 'Peso (%)']]    for i in range(0, len(all_files.keys())):        all_files[list(all_files.keys())[i]]=all_files[list(all_files.keys())[i]].sort_values('Ticker')    return all_filesdef find_tickers(datos,columna_ticker,columna_pesos):    """Given a dictionary comprised of dataframes, the column of the Tickers and the column of the weights,    this function will clean the tickers of any unwanted characters. It then adds the '.MX' suffix    and then filters each dataframe so that the only tickers that appear are the ones that the dataframes have in common.    Finally, the function accumulates the weights of the rows that were filtered out and adds them to CASH (MXN)"""    for i in range(0, len(datos.keys())):        datos[list(datos.keys())[i]][columna_ticker] = datos[list(datos.keys())[i]][columna_ticker].str.replace("*", "").str.replace(            ".", "-")    for i in range(0, len(datos.keys())):        datos[list(datos.keys())[i]][columna_ticker] = datos[list(datos.keys())[i]][columna_ticker].map('{}.MX'.format)    for i in range(0,len(datos.keys())-1):        if i==0:            common_tickers = datos[list(datos.keys())[i]][columna_ticker]        else:            common_tickers = set(common_tickers).intersection(set(datos[list(datos.keys())[i+1]][columna_ticker].values))    for i in range(0, len(datos.keys())):        datos[list(datos.keys())[i]] = datos[list(datos.keys())[i]].drop(            datos[list(datos.keys())[i]].index[~datos[list(datos.keys())[i]][columna_ticker].isin(common_tickers)])    for i in range(0,len(datos.keys())):        acum = sum(datos[list(datos.keys())[i]][columna_pesos][~datos[list(datos.keys())[i]][columna_ticker].str.contains('MXN')])        datos[list(datos.keys())[i]][columna_pesos][datos[list(datos.keys())[i]][columna_ticker].str.contains('MXN')] = 100 - acum    return common_tickers, datosdef import_prices(datos,tickers,start_date,end_date):    """ Removes the CASH of the list of tickers then imports Adj Close from    yfinance of list of tickers. Then formats date and transposes"""    tickers = list(filter(lambda k: 'MXN' not in k, tickers))    prices = yf.download(tickers, start=start_date, end=end_date)['Adj Close']    prices.index = prices.index.strftime('%Y%m%d')    prices = prices.filter(items=datos.keys(), axis=0)    prices=prices.transpose()    return prices# Passive Investmentdef shares_passive(datos, precios, cash_weight,start_date):    """Passive Investment: Returns a single column which has the amount of shares of each ticker."""    titulos = pd.DataFrame()    datos[start_date] = datos[start_date][~datos[start_date]['Ticker'].str.contains("MXN")]    titulos[start_date] = ((1000000 - (1000000 * cash_weight/100)) * datos[start_date]['Peso (%)']/100).to_numpy()/precios.loc[:,start_date].to_numpy()    titulos.index = precios.index    return titulosdef rend_p(precios, titulos, cash_weight):    """Passive Investment: Returns two dataframes. The first one is the capital in pesos at each date.    The second one is a dataframe with a column of the total capital (with cash)    at each date, the second one is the logarithmic returns between each month and    the third one is the cumulative returns."""    rend_ticker = pd.DataFrame()    rend_mensual = pd.DataFrame()    for i in precios.columns:        rend_ticker[i] = titulos.iloc[:,0].to_numpy() * precios.loc[:,i].to_numpy()    for i in rend_ticker.columns:        rend_mensual[i] = [sum(rend_ticker.loc[:,i]) + (1000000 * cash_weight/100)]    rend_mensual = rend_mensual.transpose()    rend_mensual = rend_mensual.rename(columns={0: "Capital"})    rend_mensual['Returns'] = 0    rend_mensual['Returns']=rend_mensual['Returns'].astype(float)    for i in range(0,len(rend_mensual)-1):        rend_mensual['Returns'][i+1] = np.log(rend_mensual['Capital'][i+1]/rend_mensual['Capital'][i])    rend_mensual['Cumulative Returns'] = rend_mensual['Returns'].cumsum()    return rend_ticker, rend_mensual# Active Investmentdef sharpe(prices, rf1):    """Returns the weights of an optimum portfolio based on the Markowitz Portfolio Theory.    The method uses the mean and volatility to reduce risk. The tickers with 0 weights are removed."""    pricesT=prices.T    ret = np.log(pricesT/pricesT.shift(1)).dropna()    tabla = pd.DataFrame(data={'Media':ret.mean()*252,'Volatilidad':ret.std()*(252**0.5)},                           index=ret.columns).transpose()    corr = ret.corr()    S1 =np.diag(tabla.loc['Volatilidad', :].values)    Sigma1 = S1.dot(corr).dot(S1)    Eind1 = tabla.loc['Media',:].values    n1 =len(Eind1)    w01 = np.ones(n1)/n1    bnds1=((0,1), )*n1    cons1 = {'type':'eq', 'fun':lambda w1: w1.sum() - 1}    varianza = lambda w1, Sigma1:w1.dot(Sigma1).dot(w1)    def menos_RS(w1, Eind1, Sigma1, rf1):        Ep1 = Eind1.dot(w1)        sp1 = np.sqrt(w1.dot(Sigma1).dot(w1))        RS1 = (Ep1-rf1)/sp1        return -RS1    EMV1 = minimize(fun=menos_RS,x0=w01,args=(Eind1, Sigma1, rf1),bounds=bnds1,constraints=cons1,tol=1e-10)    w_EMV1 = EMV1.x    E_EMV1 = Eind1.dot(w_EMV1)    s_EMV1 = np.sqrt(varianza(w_EMV1, Sigma1))    RS_EMV1 = (E_EMV1 - rf1)/s_EMV1    pesos = pd.DataFrame(data={'Weights': w_EMV1.round(13)})    pesos.index = prices.index    pesos = pesos[pesos['Weights'] != 0]    return pesosdef shares_active(pesos, precios, cash_weight, start_date):    """Active Investment: Returns a single column which has the amount of shares of each ticker."""    titulos = pd.DataFrame()    titulos[start_date] = ((1000000 - (1000000 * cash_weight/100)) * pesos['Weights']).to_numpy()/precios['20210129'].filter(items=pesos.index, axis=0).to_numpy()    titulos.index = pesos.index    return titulosdef rebalance(precios,titulos,rate_change,rate_rebalance):    """Function obtains the number of shares for every period where there is a rebalance.    It is based on a rate of change (positive or negative) and a rebalance rate to    increase or reduce the number of shares for the portfolio."""    for i in range(0,len(precios.columns)-1):        titulos[precios.columns[i+1]] = 0        titulos[precios.columns[i+1]] = titulos[precios.columns[i+1]].astype(float)        for j in range(0,len(titulos.index)):            if np.log(precios.iloc[i+1][j]/precios.iloc[i][j]) > rate_change:                titulos[precios.columns[i+1]][j] = titulos.iloc[j,i] * (1 + rate_rebalance)            elif np.log(precios.iloc[i+1][j]/precios.iloc[i][j]) < -rate_change:                titulos[precios.columns[i+1]][j] = titulos.iloc[j,i] * (1 - rate_rebalance)            else:                titulos[precios.columns[i+1]][j] = titulos.iloc[j,i]    return titulosdef rend_a(titulos,precios,cash_weight):    """Active Investment: Returns a dataframe with a column of the total capital (with cash)    at each date, the second one is the logarithmic returns between each month and    the third one is the cumulative returns."""    rendimientos = pd.DataFrame()    rendimientos.index = precios.columns    rendimientos['Capital'] = 0    for i in range(0,len(rendimientos)):        rendimientos['Capital'][i] = sum(titulos.iloc[:,i] * precios.filter(items=titulos.index, axis=0).iloc[:,i]) + (1000000 * cash_weight/100)    rendimientos['Returns'] = 0    rendimientos['Returns']=rendimientos['Returns'].astype(float)    for i in range(0,len(rendimientos)-1):        rendimientos['Returns'][i+1] = np.log(rendimientos['Capital'][i+1]/rendimientos['Capital'][i])    rendimientos['Cumulative Returns'] = rendimientos['Returns'].cumsum()    return rendimientosdef comission(com,precios,titulos):    """The function calculates the comission for an active portfolio.    It receives a comission rate and returns the total comission for each rebalance period."""    comision = pd.DataFrame()    comision.index = titulos.columns    comision['Comission'] = 0    comision['Comission'] = comision['Comission'].astype(float)    for i in range(0,len(comision)):        if i == 0:            comision['Comission'][i] = sum((titulos[comision.index[i]] * com) * precios.filter(items=titulos.index, axis=0)[precios.columns[i]].to_numpy())        else:            comision['Comission'][i] = sum(((abs(titulos.iloc[:,i-1] - titulos.iloc[:,i]) * com).to_numpy()) * precios.filter(items=titulos.index, axis=0)[precios.columns[i]].to_numpy())    return comisiondef operations(titulos,com,precios,comision_mensual):    """Returns a dataframe with the historic data of the active investment.    The first column has the total number of shares, the second column has the amount of shares    that needs to be bought or sold for the rebalance, the third column has the comission    rate in order to do the rebalance and the final column is the cumulative comission."""    operaciones = pd.DataFrame()    operaciones.index = titulos.columns    operaciones['Shares total'] = 0    operaciones['Shares total'] = operaciones['Shares total'].astype(float)    for i in range(0,len(titulos.columns)):        operaciones['Shares total'][i] = sum(titulos.iloc[:,i])    operaciones['Shares bought'] = 0    operaciones['Shares bought'] = operaciones['Shares bought'].astype(float)    for i in range(0,len(operaciones.index)-1):        if i == 0:            operaciones['Shares bought'][i] = operaciones['Shares total'][i]        else:            operaciones['Shares bought'][i] = abs(operaciones['Shares total'][i] - operaciones['Shares total'][i-1])    operaciones['Comission'] = comision_mensual    operaciones['Cumulative comission'] = operaciones['Comission'].cumsum()    return operaciones