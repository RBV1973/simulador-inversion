import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import base64  # Para la descarga del CSV

# Título de la aplicación
st.title("Simulador de Inversión en Acciones: Comparación de Estrategias")
st.write("Compara dos estrategias: vender cuando el precio cae por debajo de la media móvil de 50 períodos vs. no vender nunca. Usa fechas en formato YYYY-MM-DD y un ticker válido (ej. SPY, AAPL, TSLA).")

# Entradas del usuario con columnas
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.text_input("Fecha de inicio (YYYY-MM-DD)", "2020-01-01")
    fecha_fin = st.text_input("Fecha de fin (YYYY-MM-DD)", "2025-03-08")
    capital_inicial = st.number_input("Capital inicial ($)", min_value=0.0, value=1000.0, step=100.0)  # Nueva entrada
with col2:
    frecuencia = st.selectbox("Frecuencia de aportación", ["Mensual", "Semanal"])
    inversion_periodica = st.number_input(f"Inversión {frecuencia.lower()} ($)", min_value=0.0, value=500.0 if frecuencia == "Mensual" else 125.0, step=10.0)
    comision = st.number_input("Comisión por transacción ($)", min_value=0.0, value=3.0, step=1.0)
ticker = st.text_input("Ticker del activo (ej. SPY, TSLA, NVDA)", "SPY")
impuesto_venta = st.number_input("Porcentaje de impuestos por venta (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)

# Función para validar y calcular resultados de ambas estrategias
def calcular_resultados(fecha_inicio, fecha_fin, frecuencia, inversion_periodica, comision, ticker, impuesto_venta, capital_inicial):
    try:
        # Validar fechas
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
        hoy = date.today()
        if fecha_inicio_dt >= fecha_fin_dt:
            st.error("La fecha de inicio debe ser anterior a la fecha de fin.")
            return None, None
        if fecha_inicio_dt.date() > hoy or fecha_fin_dt.date() > hoy:
            st.error("Las fechas no pueden ser futuras.")
            return None, None
        
        # Calcular fecha de inicio para datos previos (5 años antes)
        fecha_inicio_previa = fecha_inicio_dt - timedelta(days=5 * 365)

        # Obtener datos históricos con 5 años adicionales
        activo = yf.download(ticker, start=fecha_inicio_previa, end=fecha_fin, progress=False)
        if activo.empty:
            st.error(f"No se encontraron datos para el ticker '{ticker}'. Verifica que sea correcto.")
            return None, None
        
        # Convertir a datos periódicos según frecuencia
        if frecuencia == "Mensual":
            precios_periodicos = activo['Close'].resample('M').last().dropna()
        else:  # Semanal
            precios_periodicos = activo['Close'].resample('W').last().dropna()
        
        # Calcular media móvil de 50 períodos con datos previos
        media_movil = precios_periodicos.rolling(window=50, min_periods=1).mean()

        # Filtrar solo el período solicitado
        precios_periodicos = precios_periodicos[fecha_inicio_dt:fecha_fin_dt]
        fechas = precios_periodicos.index
        precios = precios_periodicos.to_numpy().flatten()
        media_movil = media_movil[fecha_inicio_dt:fecha_fin_dt].to_numpy().flatten()

        # Crear DataFrames para ambas estrategias
        resultados_estrategia = pd.DataFrame({
            'Fecha': fechas,
            'Precio': precios,
            'Media_Movil_50': media_movil,
            'Acciones_Compradas': 0,
            'Acciones_Totales': 0,
            'Valor_Cartera': 0,
            'Inversion_Realizada': 0,
            'Capital_Disponible': 0,
            'Estado': 'Comprando',
            'Costo_Promedio': 0.0,
            'Impuestos_Pagados': 0.0
        })
        resultados_no_venta = pd.DataFrame({
            'Fecha': fechas,
            'Precio': precios,
            'Media_Movil_50': media_movil,
            'Acciones_Compradas': 0,
            'Acciones_Totales': 0,
            'Valor_Cartera': 0,
            'Inversion_Realizada': 0,
            'Capital_Disponible': 0,
            'Estado': 'Comprando',
            'Costo_Promedio': 0.0,
            'Impuestos_Pagados': 0.0
        })

        # Variables para estrategia con venta
        acciones_totales_est = 0
        inversion_total_est = 0
        capital_disponible_est = capital_inicial  # Inicializado con capital inicial
        en_mercado_est = True
        costo_total_acciones_est = 0.0
        costo_promedio_est = 0.0

        # Variables para estrategia sin venta
        acciones_totales_no_venta = 0
        inversion_total_no_venta = 0
        capital_disponible_no_venta = capital_inicial  # Inicializado con capital inicial
        costo_total_acciones_no_venta = 0.0
        costo_promedio_no_venta = 0.0

        for i in range(len(resultados_estrategia)):
            precio = resultados_estrategia['Precio'][i]
            media = resultados_estrategia['Media_Movil_50'][i]
            if pd.isna(precio) or precio <= 0 or pd.isna(media):
                continue

            # Aportación periódica para ambas estrategias
            capital_disponible_est += inversion_periodica
            inversion_total_est += inversion_periodica
            capital_disponible_no_venta += inversion_periodica
            inversion_total_no_venta += inversion_periodica

            # Estrategia con venta
            if en_mercado_est and precio < media:
                valor_venta = acciones_totales_est * precio
                ganancia = max(0, valor_venta - costo_total_acciones_est)
                impuestos = ganancia * (impuesto_venta / 100)
                capital_disponible_est += valor_venta - impuestos - comision
                inversion_total_est += comision
                resultados_estrategia.at[i, 'Impuestos_Pagados'] = impuestos
                acciones_totales_est = 0
                costo_total_acciones_est = 0.0
                costo_promedio_est = 0.0
                en_mercado_est = False
                resultados_estrategia.at[i, 'Estado'] = 'Vendiendo'
            elif not en_mercado_est and precio > media:
                en_mercado_est = True
                resultados_estrategia.at[i, 'Estado'] = 'Reingresando'

            if en_mercado_est:
                acciones_compradas_est = int((capital_disponible_est - comision) / precio)
                if acciones_compradas_est < 1:
                    acciones_compradas_est = 0
                costo_acciones_est = acciones_compradas_est * precio
                costo_total_est = costo_acciones_est + (comision if acciones_compradas_est > 0 else 0)
                capital_disponible_est -= costo_total_est
                acciones_totales_est += acciones_compradas_est
                costo_total_acciones_est += costo_acciones_est
                costo_promedio_est = costo_total_acciones_est / acciones_totales_est if acciones_totales_est > 0 else 0.0
                resultados_estrategia.at[i, 'Acciones_Compradas'] = acciones_compradas_est
                resultados_estrategia.at[i, 'Estado'] = 'Comprando'
            elif not en_mercado_est:
                resultados_estrategia.at[i, 'Estado'] = 'Esperando'

            resultados_estrategia.at[i, 'Acciones_Totales'] = acciones_totales_est
            resultados_estrategia.at[i, 'Valor_Cartera'] = acciones_totales_est * precio
            resultados_estrategia.at[i, 'Inversion_Realizada'] = inversion_total_est
            resultados_estrategia.at[i, 'Capital_Disponible'] = capital_disponible_est
            resultados_estrategia.at[i, 'Costo_Promedio'] = costo_promedio_est

            # Estrategia sin venta (siempre compra)
            acciones_compradas_no_venta = int((capital_disponible_no_venta - comision) / precio)
            if acciones_compradas_no_venta < 1:
                acciones_compradas_no_venta = 0
            costo_acciones_no_venta = acciones_compradas_no_venta * precio
            costo_total_no_venta = costo_acciones_no_venta + (comision if acciones_compradas_no_venta > 0 else 0)
            capital_disponible_no_venta -= costo_total_no_venta
            acciones_totales_no_venta += acciones_compradas_no_venta
            costo_total_acciones_no_venta += costo_acciones_no_venta
            costo_promedio_no_venta = costo_total_acciones_no_venta / acciones_totales_no_venta if acciones_totales_no_venta > 0 else 0.0
            resultados_no_venta.at[i, 'Acciones_Compradas'] = acciones_compradas_no_venta
            resultados_no_venta.at[i, 'Acciones_Totales'] = acciones_totales_no_venta
            resultados_no_venta.at[i, 'Valor_Cartera'] = acciones_totales_no_venta * precio
            resultados_no_venta.at[i, 'Inversion_Realizada'] = inversion_total_no_venta
            resultados_no_venta.at[i, 'Capital_Disponible'] = capital_disponible_no_venta
            resultados_no_venta.at[i, 'Costo_Promedio'] = costo_promedio_no_venta
            resultados_no_venta.at[i, 'Estado'] = 'Comprando'
            resultados_no_venta.at[i, 'Impuestos_Pagados'] = 0.0

        return resultados_estrategia, resultados_no_venta

    except ValueError as e:
        st.error(f"Error en el formato de las fechas: {str(e)}. Usa YYYY-MM-DD.")
        return None, None
    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return None, None

# Función para generar enlace de descarga de CSV con formato personalizado
def descargar_csv(df, filename="resultados_inversion.csv"):
    df_csv = df.copy()
    df_csv['Fecha'] = df_csv['Fecha'].dt.strftime('%Y-%m-%d')
    for col in ['Precio', 'Media_Movil_50', 'Valor_Cartera', 'Inversion_Realizada', 'Capital_Disponible', 'Costo_Promedio', 'Impuestos_Pagados']:
        df_csv[col] = df_csv[col].apply(lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    csv = df_csv.to_csv(index=False, decimal=',', sep=';')
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Descargar {filename}</a>'
    return href

# Función para formatear números en la tabla
def format_number(x):
    return f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Botón para ejecutar la simulación
if st.button("Calcular"):
    resultados_estrategia, resultados_no_venta = calcular_resultados(fecha_inicio, fecha_fin, frecuencia, inversion_periodica, comision, ticker, impuesto_venta, capital_inicial)
    
    if resultados_estrategia is not None and resultados_no_venta is not None:
        # Resultados numéricos para estrategia con venta
        inversion_total_est = round(resultados_estrategia['Inversion_Realizada'].iloc[-1], 2)
        capital_sobrante_est = round(resultados_estrategia['Capital_Disponible'].iloc[-1], 2)
        acciones_totales_est = resultados_estrategia['Acciones_Totales'].iloc[-1]
        valor_cartera_est = round(resultados_estrategia['Valor_Cartera'].iloc[-1], 2)
        ganancia_perdida_est = round(valor_cartera_est + capital_sobrante_est - inversion_total_est, 2)
        rendimiento_est = round((ganancia_perdida_est / inversion_total_est) * 100, 2) if inversion_total_est > 0 else 0

        # Resultados numéricos para estrategia sin venta
        inversion_total_no_venta = round(resultados_no_venta['Inversion_Realizada'].iloc[-1], 2)
        capital_sobrante_no_venta = round(resultados_no_venta['Capital_Disponible'].iloc[-1], 2)
        acciones_totales_no_venta = resultados_no_venta['Acciones_Totales'].iloc[-1]
        valor_cartera_no_venta = round(resultados_no_venta['Valor_Cartera'].iloc[-1], 2)
        ganancia_perdida_no_venta = round(valor_cartera_no_venta + capital_sobrante_no_venta - inversion_total_no_venta, 2)
        rendimiento_no_venta = round((ganancia_perdida_no_venta / inversion_total_no_venta) * 100, 2) if inversion_total_no_venta > 0 else 0

        st.subheader("Resultados Comparativos")
        st.write("**Estrategia con venta (cuando precio < media móvil 50):**")
        st.write(f"- Inversión total aportada (incluye capital inicial): ${format_number(inversion_total_est + capital_inicial)}")
        st.write(f"- Capital sobrante: ${format_number(capital_sobrante_est)}")
        st.write(f"- Número total de acciones: {acciones_totales_est}")
        st.write(f"- Valor final de la cartera: ${format_number(valor_cartera_est)}")
        st.write(f"- Ganancia/Pérdida: ${format_number(ganancia_perdida_est)} ({format_number(rendimiento_est)}%)")

        st.write("**Estrategia sin venta:**")
        st.write(f"- Inversión total aportada (incluye capital inicial): ${format_number(inversion_total_no_venta + capital_inicial)}")
        st.write(f"- Capital sobrante: ${format_number(capital_sobrante_no_venta)}")
        st.write(f"- Número total de acciones: {acciones_totales_no_venta}")
        st.write(f"- Valor final de la cartera: ${format_number(valor_cartera_no_venta)}")
        st.write(f"- Ganancia/Pérdida: ${format_number(ganancia_perdida_no_venta)} ({format_number(rendimiento_no_venta)}%)")

        # Gráfico comparativo con inversión realizada
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=resultados_estrategia['Fecha'], y=resultados_estrategia['Valor_Cartera'], 
                                 mode='lines', name='Estrategia con venta', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=resultados_no_venta['Fecha'], y=resultados_no_venta['Valor_Cartera'], 
                                 mode='lines', name='Estrategia sin venta', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=resultados_estrategia['Fecha'], y=resultados_estrategia['Inversion_Realizada'] + capital_inicial, 
                                 mode='lines', name='Inversión Realizada (con capital inicial)', line=dict(color='darkgreen', dash='dash')))
        fig.update_layout(
            title=f"Comparación de Estrategias en {ticker} ({frecuencia})",
            xaxis_title="Fecha",
            yaxis_title="Valor ($)",
            legend=dict(x=0, y=1),
            template="plotly_white"
        )
        st.plotly_chart(fig)

        # Mostrar tablas siempre visibles
        st.subheader(f"Detalles {frecuencia}es - Estrategia con venta")
        resultados_est_display = resultados_estrategia.copy()
        resultados_est_display['Fecha'] = resultados_est_display['Fecha'].dt.strftime('%Y-%m-%d')
        st.dataframe(resultados_est_display.style.format({
            'Precio': format_number,
            'Media_Movil_50': format_number,
            'Valor_Cartera': format_number,
            'Inversion_Realizada': format_number,
            'Capital_Disponible': format_number,
            'Costo_Promedio': format_number,
            'Impuestos_Pagados': format_number
        }))

        st.subheader(f"Detalles {frecuencia}es - Estrategia sin venta")
        resultados_no_venta_display = resultados_no_venta.copy()
        resultados_no_venta_display['Fecha'] = resultados_no_venta_display['Fecha'].dt.strftime('%Y-%m-%d')
        st.dataframe(resultados_no_venta_display.style.format({
            'Precio': format_number,
            'Media_Movil_50': format_number,
            'Valor_Cartera': format_number,
            'Inversion_Realizada': format_number,
            'Capital_Disponible': format_number,
            'Costo_Promedio': format_number,
            'Impuestos_Pagados': format_number
        }))

        # Botones de descarga
        st.markdown(descargar_csv(resultados_estrategia, "resultados_estrategia_con_venta.csv"), unsafe_allow_html=True)
        st.markdown(descargar_csv(resultados_no_venta, "resultados_estrategia_sin_venta.csv"), unsafe_allow_html=True)

# Nota al pie
st.write("Nota: Los datos provienen de Yahoo Finance. La estrategia con venta aplica impuestos solo a las ganancias (precio de venta > costo promedio). La línea verde oscura muestra la inversión total realizada incluyendo el capital inicial.")
