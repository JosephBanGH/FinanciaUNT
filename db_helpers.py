# utils/db_helpers.py
"""
Utilidades y helpers para el sistema de mantenedores
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st

class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass

class DataValidator:
    """Clase para validar datos antes de insertar en la base de datos"""
    
    @staticmethod
    def validar_email(email: str) -> bool:
        """Validar formato de email"""
        import re
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(patron, email) is not None
    
    @staticmethod
    def validar_monto(monto: float) -> bool:
        """Validar que el monto sea positivo"""
        return monto > 0
    
    @staticmethod
    def validar_fecha(fecha: str) -> bool:
        """Validar formato de fecha YYYY-MM-DD"""
        try:
            datetime.strptime(fecha, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validar_usuario(email: str, nombre: str) -> Dict:
        """Validar datos completos de usuario"""
        errores = []
        
        if not email or len(email) < 5:
            errores.append("Email inválido o muy corto")
        elif not DataValidator.validar_email(email):
            errores.append("Formato de email inválido")
        
        if not nombre or len(nombre) < 2:
            errores.append("Nombre inválido o muy corto")
        
        return {"valido": len(errores) == 0, "errores": errores}
    
    @staticmethod
    def validar_transaccion(monto: float, categoria: str, descripcion: str, 
                           fecha: str, tipo: str) -> Dict:
        """Validar datos completos de transacción"""
        errores = []
        
        if not DataValidator.validar_monto(monto):
            errores.append("El monto debe ser mayor a 0")
        
        if not categoria or len(categoria) < 2:
            errores.append("Categoría inválida")
        
        if not descripcion or len(descripcion) < 3:
            errores.append("Descripción muy corta (mínimo 3 caracteres)")
        
        if not DataValidator.validar_fecha(fecha):
            errores.append("Fecha inválida (formato: YYYY-MM-DD)")
        
        if tipo not in ['ingreso', 'gasto']:
            errores.append("Tipo debe ser 'ingreso' o 'gasto'")
        
        return {"valido": len(errores) == 0, "errores": errores}

class DataExporter:
    """Clase para exportar datos a diferentes formatos"""
    
    @staticmethod
    def exportar_csv(df: pd.DataFrame, nombre_archivo: str = "datos.csv"):
        """Exportar DataFrame a CSV"""
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=nombre_archivo,
            mime="text/csv",
        )
    
    @staticmethod
    def exportar_excel(df: pd.DataFrame, nombre_archivo: str = "datos.xlsx"):
        """Exportar DataFrame a Excel"""
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Datos')
        
        st.download_button(
            label="📥 Descargar Excel",
            data=output.getvalue(),
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    @staticmethod
    def exportar_json(df: pd.DataFrame, nombre_archivo: str = "datos.json"):
        """Exportar DataFrame a JSON"""
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Descargar JSON",
            data=json_str,
            file_name=nombre_archivo,
            mime="application/json"
        )

class DataAnalyzer:
    """Clase para análisis de datos"""
    
    @staticmethod
    def analizar_transacciones(df_transacciones: pd.DataFrame) -> Dict:
        """Análisis completo de transacciones"""
        if df_transacciones.empty:
            return {
                "total_transacciones": 0,
                "total_ingresos": 0,
                "total_gastos": 0,
                "balance": 0,
                "promedio_gasto": 0,
                "categoria_mas_gasto": None
            }
        
        ingresos = df_transacciones[df_transacciones['tipo'] == 'ingreso']['monto'].sum()
        gastos = df_transacciones[df_transacciones['tipo'] == 'gasto']['monto'].sum()
        
        gastos_por_categoria = df_transacciones[
            df_transacciones['tipo'] == 'gasto'
        ].groupby('categoria')['monto'].sum()
        
        categoria_max = gastos_por_categoria.idxmax() if not gastos_por_categoria.empty else None
        
        return {
            "total_transacciones": len(df_transacciones),
            "total_ingresos": float(ingresos),
            "total_gastos": float(gastos),
            "balance": float(ingresos - gastos),
            "promedio_gasto": float(df_transacciones[df_transacciones['tipo']=='gasto']['monto'].mean()) if len(df_transacciones[df_transacciones['tipo']=='gasto']) > 0 else 0,
            "categoria_mas_gasto": categoria_max,
            "monto_categoria_max": float(gastos_por_categoria.max()) if not gastos_por_categoria.empty else 0
        }
    
    @staticmethod
    def detectar_gastos_inusuales(df_transacciones: pd.DataFrame, 
                                  umbral_desviacion: float = 2.0) -> pd.DataFrame:
        """Detectar gastos que exceden el umbral de desviación estándar"""
        gastos = df_transacciones[df_transacciones['tipo'] == 'gasto'].copy()
        
        if gastos.empty:
            return pd.DataFrame()
        
        mean = gastos['monto'].mean()
        std = gastos['monto'].std()
        
        gastos_inusuales = gastos[gastos['monto'] > mean + (umbral_desviacion * std)]
        
        return gastos_inusuales
    
    @staticmethod
    def calcular_tendencia(df_transacciones: pd.DataFrame, dias: int = 30) -> Dict:
        """Calcular tendencia de gastos"""
        if df_transacciones.empty:
            return {"tendencia": "neutral", "variacion_porcentual": 0}
        
        df_transacciones['fecha'] = pd.to_datetime(df_transacciones['fecha'])
        
        fecha_limite = datetime.now() - timedelta(days=dias)
        fecha_mitad = datetime.now() - timedelta(days=dias//2)
        
        primera_mitad = df_transacciones[
            (df_transacciones['fecha'] >= fecha_limite) & 
            (df_transacciones['fecha'] < fecha_mitad) &
            (df_transacciones['tipo'] == 'gasto')
        ]['monto'].sum()
        
        segunda_mitad = df_transacciones[
            (df_transacciones['fecha'] >= fecha_mitad) &
            (df_transacciones['tipo'] == 'gasto')
        ]['monto'].sum()
        
        if primera_mitad == 0:
            return {"tendencia": "sin_datos", "variacion_porcentual": 0}
        
        variacion = ((segunda_mitad - primera_mitad) / primera_mitad) * 100
        
        if variacion > 10:
            tendencia = "creciente"
        elif variacion < -10:
            tendencia = "decreciente"
        else:
            tendencia = "estable"
        
        return {
            "tendencia": tendencia,
            "variacion_porcentual": round(variacion, 2),
            "gasto_periodo_1": float(primera_mitad),
            "gasto_periodo_2": float(segunda_mitad)
        }

class AlertGenerator:
    """Generador automático de alertas"""
    
    @staticmethod
    def verificar_presupuestos(df_transacciones: pd.DataFrame, 
                               df_presupuestos: pd.DataFrame,
                               usuario_id: str) -> List[Dict]:
        """Verificar si se exceden presupuestos"""
        alertas = []
        
        if df_transacciones.empty or df_presupuestos.empty:
            return alertas
        
        gastos_usuario = df_transacciones[
            (df_transacciones['usuario_id'] == usuario_id) &
            (df_transacciones['tipo'] == 'gasto')
        ]
        
        if gastos_usuario.empty:
            return alertas
        
        gastos_por_categoria = gastos_usuario.groupby('categoria')['monto'].sum()
        
        presupuestos_usuario = df_presupuestos[
            df_presupuestos['usuario_id'] == usuario_id
        ]
        
        for _, presupuesto in presupuestos_usuario.iterrows():
            categoria = presupuesto['categoria']
            limite = presupuesto['monto_maximo']
            
            if categoria in gastos_por_categoria.index:
                gasto_actual = gastos_por_categoria[categoria]
                porcentaje = (gasto_actual / limite) * 100
                
                if gasto_actual > limite:
                    alertas.append({
                        'tipo': 'presupuesto_excedido',
                        'severidad': 'alta',
                        'mensaje': f"Has excedido el presupuesto en {categoria} por ${gasto_actual - limite:.2f} ({porcentaje:.1f}%)",
                        'categoria': categoria,
                        'gasto_actual': float(gasto_actual),
                        'limite': float(limite)
                    })
                elif porcentaje >= 80:
                    alertas.append({
                        'tipo': 'presupuesto_cerca_limite',
                        'severidad': 'media',
                        'mensaje': f"Estás cerca del límite en {categoria}: ${gasto_actual:.2f} de ${limite:.2f} ({porcentaje:.1f}%)",
                        'categoria': categoria,
                        'gasto_actual': float(gasto_actual),
                        'limite': float(limite)
                    })
        
        return alertas
    
    @staticmethod
    def detectar_patrones_inusuales(df_transacciones: pd.DataFrame) -> List[Dict]:
        """Detectar patrones de gasto inusuales"""
        alertas = []
        
        gastos_inusuales = DataAnalyzer.detectar_gastos_inusuales(df_transacciones)
        
        for _, gasto in gastos_inusuales.iterrows():
            alertas.append({
                'tipo': 'gasto_inusual',
                'severidad': 'media',
                'mensaje': f"Gasto inusual detectado: ${gasto['monto']:.2f} en {gasto['categoria']} - {gasto['descripcion']}",
                'monto': float(gasto['monto']),
                'categoria': gasto['categoria']
            })
        
        return alertas

class ReportGenerator:
    """Generador de reportes"""
    
    @staticmethod
    def generar_reporte_mensual(usuario_id: str, mes: int, anio: int,
                               df_transacciones: pd.DataFrame,
                               df_presupuestos: pd.DataFrame) -> Dict:
        """Generar reporte mensual completo"""
        
        # Filtrar transacciones del mes
        df_transacciones['fecha'] = pd.to_datetime(df_transacciones['fecha'])
        transacciones_mes = df_transacciones[
            (df_transacciones['usuario_id'] == usuario_id) &
            (df_transacciones['fecha'].dt.month == mes) &
            (df_transacciones['fecha'].dt.year == anio)
        ]
        
        # Análisis
        analisis = DataAnalyzer.analizar_transacciones(transacciones_mes)
        tendencia = DataAnalyzer.calcular_tendencia(transacciones_mes, 30)
        alertas = AlertGenerator.verificar_presupuestos(
            transacciones_mes, df_presupuestos, usuario_id
        )
        
        return {
            "periodo": f"{mes}/{anio}",
            "analisis": analisis,
            "tendencia": tendencia,
            "alertas": alertas,
            "total_transacciones": len(transacciones_mes)
        }

# Funciones de ayuda para Streamlit
def mostrar_mensaje_error(errores: List[str]):
    """Mostrar múltiples mensajes de error"""
    for error in errores:
        st.error(f"❌ {error}")

def mostrar_confirmacion_eliminacion(item: str) -> bool:
    """Mostrar diálogo de confirmación para eliminación"""
    if f'confirmar_eliminar_{item}' not in st.session_state:
        st.session_state[f'confirmar_eliminar_{item}'] = False
    
    if st.session_state[f'confirmar_eliminar_{item}']:
        st.warning("⚠️ ¿Está seguro? Esta acción no se puede deshacer.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar", key=f"confirmar_si_{item}"):
                st.session_state[f'confirmar_eliminar_{item}'] = False
                return True
        with col2:
            if st.button("❌ Cancelar", key=f"confirmar_no_{item}"):
                st.session_state[f'confirmar_eliminar_{item}'] = False
                return False
    else:
        if st.button("🗑️ Eliminar", key=f"btn_eliminar_{item}"):
            st.session_state[f'confirmar_eliminar_{item}'] = True
            st.rerun()
    
    return False

def formatear_moneda(monto: float, simbolo: str = "$") -> str:
    """Formatear monto como moneda"""
    return f"{simbolo}{monto:,.2f}"

def crear_badge_severidad(severidad: str) -> str:
    """Crear badge HTML para severidad"""
    colores = {
        'baja': '#28a745',
        'media': '#ffc107',
        'alta': '#dc3545'
    }
    color = colores.get(severidad, '#6c757d')
    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold;">{severidad.upper()}</span>'

def crear_badge_estado(estado: bool, texto_activo: str = "Activo", 
                      texto_inactivo: str = "Inactivo") -> str:
    """Crear badge HTML para estado"""
    color = '#28a745' if estado else '#dc3545'
    texto = texto_activo if estado else texto_inactivo
    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold;">{texto}</span>'