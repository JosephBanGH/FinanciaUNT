import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
from supabase import create_client, Client
from typing import Dict, List, Optional
import uuid
from fpdf import FPDF
import io
import base64
import requests
from auth import main_auth


# Configuración de la página
st.set_page_config(
    page_title="Asesor Financiero Personal IA",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== MANAGERS ====================

class DatabaseManager:
    """Gestor de conexión con Supabase"""
    def __init__(self):
        try:
            self.supabase_url = st.secrets.get("SUPABASE_URL")
            self.supabase_key = st.secrets.get("SUPABASE_KEY")
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            st.error(f"Error conectando a Supabase: {str(e)}")
            self.client = None
    
    def get_client(self) -> Client:
        return self.client

class UsuarioManager:
    """Mantenedor de Usuarios"""
    def __init__(self, db: DatabaseManager):
        self.db = db.get_client()
    
    def listar_usuarios(self) -> pd.DataFrame:
        try:
            response = self.db.table('usuarios').select('*').order('fecha_registro', desc=True).execute()
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def crear_usuario(self, email: str, nombre: str, plan: str = 'basico') -> Dict:
        data = {
            'email': email,
            'nombre': nombre,
            'plan_suscripcion': plan,
            'configuracion': {}
        }
        response = self.db.table('usuarios').insert(data).execute()
        return response.data[0] if response.data else None
    
    def actualizar_usuario(self, usuario_id: str, datos: Dict) -> Dict:
        response = self.db.table('usuarios').update(datos).eq('id', usuario_id).execute()
        return response.data[0] if response.data else None
    
    def eliminar_usuario(self, usuario_id: str) -> bool:
        try:
            self.db.table('presupuestos').delete().eq('usuario_id', usuario_id).execute()
            self.db.table('transacciones').delete().eq('usuario_id', usuario_id).execute()
            self.db.table('alertas').delete().eq('usuario_id', usuario_id).execute()
            self.db.table('analisis_financiero').delete().eq('usuario_id', usuario_id).execute()
            self.db.table('inversiones').delete().eq('usuario_id', usuario_id).execute()
            self.db.table('suscripciones').delete().eq('usuario_id', usuario_id).execute()
            response = self.db.table('usuarios').delete().eq('id', usuario_id).execute()
            return True if response.data else False
        except Exception as e:
            st.error(f"Error eliminando usuario: {str(e)}")
            return False

class TransaccionManager:
    """Mantenedor de Transacciones"""
    def __init__(self, db: DatabaseManager):
        self.db = db.get_client()
        self.supabase_url = st.secrets.get("SUPABASE_URL", "https://tu-proyecto.supabase.co")
        self.supabase_key = st.secrets.get("SUPABASE_KEY", "tu-clave-supabase")
        self.n8n_webhook = st.secrets.get("N8N_WEBHOOK", "")
        
    
    def listar_transacciones(self, usuario_id: Optional[str] = None, dias: int = 30) -> pd.DataFrame:
        try:
            fecha_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
            query = self.db.table('transacciones').select('*').gte('fecha', fecha_inicio)
            if usuario_id:
                query = query.eq('usuario_id', usuario_id)
            response = query.order('fecha', desc=True).execute()
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def crear_transaccion(self, usuario_id: str, monto: float, categoria: str, 
                         descripcion: str, fecha: str, tipo: str, cuenta: str = '') -> Dict:
        data = {
            'usuario_id': usuario_id,
            'monto': monto,
            'categoria': categoria,
            'descripcion': descripcion,
            'fecha': fecha,
            'tipo': tipo,
            'cuenta': cuenta,
            'metadata': {}
        }
        response = self.db.table('transacciones').insert(data).execute()
        return response.data[0] if response.data else None
    
    def actualizar_transaccion(self, transaccion_id: str, datos: Dict) -> Dict:
        response = self.db.table('transacciones').update(datos).eq('id', transaccion_id).execute()
        return response.data[0] if response.data else None
    
    def eliminar_transaccion(self, transaccion_id: str) -> bool:
        response = self.db.table('transacciones').delete().eq('id', transaccion_id).execute()
        return True if response.data else False

class PresupuestoManager:
    """Mantenedor de Presupuestos"""
    def __init__(self, db: DatabaseManager):
        self.db = db.get_client()
    
    def listar_presupuestos(self, usuario_id: Optional[str] = None) -> pd.DataFrame:
        try:
            query = self.db.table('presupuestos').select('*')
            if usuario_id:
                query = query.eq('usuario_id', usuario_id)
            response = query.order('categoria').execute()
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def crear_presupuesto(self, usuario_id: str, categoria: str, 
                         monto_maximo: float, periodo: str = 'mensual') -> Dict:
        data = {
            'usuario_id': usuario_id,
            'categoria': categoria,
            'monto_maximo': monto_maximo,
            'periodo': periodo
        }
        response = self.db.table('presupuestos').insert(data).execute()
        return response.data[0] if response.data else None
    
    def actualizar_presupuesto(self, presupuesto_id: str, datos: Dict) -> Dict:
        response = self.db.table('presupuestos').update(datos).eq('id', presupuesto_id).execute()
        return response.data[0] if response.data else None
    
    def eliminar_presupuesto(self, presupuesto_id: str) -> bool:
        response = self.db.table('presupuestos').delete().eq('id', presupuesto_id).execute()
        return True if response.data else False

class AlertaManager:
    """Mantenedor de Alertas"""
    def __init__(self, db: DatabaseManager):
        self.db = db.get_client()
    
    def listar_alertas(self, usuario_id: Optional[str] = None, solo_no_leidas: bool = False) -> pd.DataFrame:
        try:
            query = self.db.table('alertas').select('*')
            if usuario_id:
                query = query.eq('usuario_id', usuario_id)
            if solo_no_leidas:
                query = query.eq('leida', False)
            response = query.order('created_at', desc=True).execute()
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def crear_alerta(self, usuario_id: str, tipo: str, mensaje: str, 
                    severidad: str = 'media') -> Dict:
        data = {
            'usuario_id': usuario_id,
            'tipo': tipo,
            'mensaje': mensaje,
            'severidad': severidad,
            'leida': False
        }
        response = self.db.table('alertas').insert(data).execute()
        return response.data[0] if response.data else None
    
    def marcar_leida(self, alerta_id: str) -> bool:
        response = self.db.table('alertas').update({'leida': True}).eq('id', alerta_id).execute()
        return True if response.data else False

class AsesorFinanciero:
    """Clase principal para análisis financiero"""
    def __init__(self, transaccion_mgr: TransaccionManager, presupuesto_mgr: PresupuestoManager):
        self.transaccion_mgr = transaccion_mgr
        self.presupuesto_mgr = presupuesto_mgr
        self.n8n_webhook = st.secrets.get("N8N_WEBHOOK", "")
    
    def get_analisis_ia(self, transacciones: pd.DataFrame, presupuestos: pd.DataFrame):
        """Generar análisis con IA"""
        if transacciones.empty:
            return {
                'resumen': {
                    'total_ingresos': 0,
                    'total_gastos': 0,
                    'ahorro_neto': 0,
                    'tasa_ahorro': 0
                },
                'recomendaciones': ["No hay suficientes datos para generar recomendaciones"],
                'alertas': [],
                'predicciones': {
                    'ahorro_3_meses': 0,
                    'proyeccion_gastos': 0
                }
            }
        
        gastos_por_categoria = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum()
        total_gastos = gastos_por_categoria.sum()
        total_ingresos = transacciones[transacciones['tipo'] == 'ingreso']['monto'].sum()
        
        recomendaciones = []
        alertas = []
        
        # Análisis de presupuestos
        if not presupuestos.empty:
            presupuestos_dict = presupuestos.set_index('categoria')['monto_maximo'].to_dict()
            for categoria, gasto in gastos_por_categoria.items():
                if categoria in presupuestos_dict:
                    presupuesto = presupuestos_dict[categoria]
                    porcentaje = (gasto / presupuesto) * 100
                    if porcentaje > 90:
                        alertas.append(f"Gastos en {categoria} al {porcentaje:.1f}% del presupuesto")
                    elif porcentaje > 100:
                        alertas.append(f"¡Presupuesto excedido en {categoria}! ({porcentaje:.1f}%)")
        
        # Recomendaciones generales
        if total_ingresos > 0:
            tasa_ahorro = ((total_ingresos - total_gastos) / total_ingresos * 100)
            if tasa_ahorro < 10:
                recomendaciones.append("Considera aumentar tu tasa de ahorro al menos al 10% de tus ingresos")
            elif tasa_ahorro > 30:
                recomendaciones.append("¡Excelente! Estás ahorrando más del 30% de tus ingresos")
        
        if not gastos_por_categoria.empty:
            categoria_mayor = gastos_por_categoria.idxmax()
            recomendaciones.append(f"Tu mayor gasto es en {categoria_mayor}. Revisa si puedes optimizarlo")
        
        analisis = {
            'resumen': {
                'total_ingresos': float(total_ingresos),
                'total_gastos': float(total_gastos),
                'ahorro_neto': float(total_ingresos - total_gastos),
                'tasa_ahorro': float(((total_ingresos - total_gastos) / total_ingresos * 100) if total_ingresos > 0 else 0)
            },
            'recomendaciones': recomendaciones if recomendaciones else ["Continúa registrando tus transacciones para mejores análisis"],
            'alertas': alertas,
            'predicciones': {
                'ahorro_3_meses': float((total_ingresos - total_gastos) * 3 * 1.05),
                'proyeccion_gastos': float(total_gastos * 1.02)
            }
        }
        
        return analisis

# ==================== PDF REPORT ====================

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Reporte Financiero Personal', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.set_text_color(0, 0, 0)
        self.ln(5)
    
    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 8, body)
        self.ln()
    
    def add_metric(self, label, value):
        self.set_font('Arial', 'B', 11)
        self.cell(60, 8, label + ':', 0, 0)
        self.set_font('Arial', '', 11)
        self.cell(0, 8, str(value), 0, 1)
    
    def add_image_from_bytes(self, img_bytes, x=None, y=None, w=0, h=0):
        """Agregar imagen desde bytes"""
        # Guardar temporalmente la imagen
        temp_file = f"temp_chart_{datetime.now().timestamp()}.png"
        with open(temp_file, 'wb') as f:
            f.write(img_bytes)
        
        # Agregar al PDF
        if x is None:
            x = self.get_x()
        if y is None:
            y = self.get_y()
        
        self.image(temp_file, x=x, y=y, w=w, h=h)
        
        # Limpiar archivo temporal
        import os
        try:
            os.remove(temp_file)
        except:
            pass


def generar_graficos(transacciones: pd.DataFrame, analisis: Dict) -> Dict[str, bytes]:
    """Generar gráficos en formato PNG para el PDF"""
    graficos = {}
    
    if transacciones.empty:
        return graficos
    
    try:
        # 1. Gráfico de distribución de gastos (pie chart)
        gastos_categoria = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum()
        if not gastos_categoria.empty:
            fig = px.pie(
                values=gastos_categoria.values,
                names=gastos_categoria.index,
                title='Distribucion de Gastos por Categoria',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(
                width=700,
                height=500,
                showlegend=True,
                font=dict(size=12)
            )
            graficos['distribucion_gastos'] = fig.to_image(format="png", width=700, height=500)
        
        # 2. Gráfico de tendencias (line chart)
        transacciones_copy = transacciones.copy()
        transacciones_copy['fecha'] = pd.to_datetime(transacciones_copy['fecha'])
        gastos_diarios = transacciones_copy[transacciones_copy['tipo'] == 'gasto'].groupby('fecha')['monto'].sum().reset_index()
        
        if not gastos_diarios.empty:
            fig = px.line(
                gastos_diarios,
                x='fecha',
                y='monto',
                title='Tendencia de Gastos Diarios',
                markers=True
            )
            fig.update_layout(
                width=700,
                height=400,
                xaxis_title='Fecha',
                yaxis_title='Monto ($)',
                font=dict(size=12)
            )
            graficos['tendencia_gastos'] = fig.to_image(format="png", width=700, height=400)
        
        # 3. Gráfico de resumen (métricas)
        fig = go.Figure()
        
        categorias_metricas = ['Ingresos', 'Gastos', 'Ahorro Neto']
        valores_metricas = [
            analisis['resumen']['total_ingresos'],
            analisis['resumen']['total_gastos'],
            analisis['resumen']['ahorro_neto']
        ]
        colores = ['#00CC96', '#EF553B', '#636EFA']
        
        fig.add_trace(go.Bar(
            x=categorias_metricas,
            y=valores_metricas,
            marker_color=colores,
            text=[f'${v:,.2f}' for v in valores_metricas],
            textposition='auto',
        ))
        
        fig.update_layout(
            title='Resumen Financiero',
            width=700,
            height=400,
            xaxis_title='',
            yaxis_title='Monto ($)',
            showlegend=False,
            font=dict(size=12)
        )
        
        graficos['resumen_financiero'] = fig.to_image(format="png", width=700, height=400)
        
    except Exception as e:
        print(f"Error generando gráficos: {str(e)}")
    
    return graficos


def generar_reporte_pdf(usuario_nombre: str, transacciones: pd.DataFrame, 
                        analisis: Dict, presupuestos: pd.DataFrame) -> bytes:
    """Generar reporte PDF completo con gráficos"""
    
    # Generar gráficos
    graficos = generar_graficos(transacciones, analisis)
    
    pdf = PDFReport()
    pdf.add_page()
    
    # Información del usuario
    pdf.chapter_title('INFORMACION DEL USUARIO')
    pdf.add_metric('Usuario', usuario_nombre)
    pdf.add_metric('Periodo analizado', f'{len(transacciones)} transacciones')
    pdf.ln(5)
    
    # Resumen ejecutivo
    pdf.chapter_title('RESUMEN EJECUTIVO')
    pdf.add_metric('Ingresos totales', f"${analisis['resumen']['total_ingresos']:,.2f}")
    pdf.add_metric('Gastos totales', f"${analisis['resumen']['total_gastos']:,.2f}")
    pdf.add_metric('Ahorro neto', f"${analisis['resumen']['ahorro_neto']:,.2f}")
    pdf.add_metric('Tasa de ahorro', f"{analisis['resumen']['tasa_ahorro']:.1f}%")
    pdf.ln(5)
    
    # Agregar gráfico de resumen financiero
    if 'resumen_financiero' in graficos:
        pdf.chapter_title('GRAFICO: RESUMEN FINANCIERO')
        pdf.add_image_from_bytes(graficos['resumen_financiero'], x=10, w=190)
        pdf.ln(10)
    
    # Nueva página para distribución de gastos
    pdf.add_page()
    
    # Análisis por categorías (tabla)
    if not transacciones.empty:
        pdf.chapter_title('GASTOS POR CATEGORIA')
        gastos_cat = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum().sort_values(ascending=False)
        
        for categoria, monto in gastos_cat.items():
            porcentaje = (monto / analisis['resumen']['total_gastos'] * 100) if analisis['resumen']['total_gastos'] > 0 else 0
            pdf.set_font('Arial', '', 10)
            pdf.cell(70, 7, f'  {categoria}', 0, 0)
            pdf.cell(50, 7, f'${monto:,.2f}', 0, 0)
            pdf.cell(0, 7, f'({porcentaje:.1f}%)', 0, 1)
        pdf.ln(5)
    
    # Agregar gráfico de distribución
    if 'distribucion_gastos' in graficos:
        pdf.chapter_title('GRAFICO: DISTRIBUCION DE GASTOS')
        pdf.add_image_from_bytes(graficos['distribucion_gastos'], x=10, w=190)
        pdf.ln(10)
    
    # Nueva página para tendencias
    pdf.add_page()
    
    # Agregar gráfico de tendencias
    if 'tendencia_gastos' in graficos:
        pdf.chapter_title('GRAFICO: TENDENCIA DE GASTOS')
        pdf.add_image_from_bytes(graficos['tendencia_gastos'], x=10, w=190)
        pdf.ln(10)
    
    # Comparación con presupuestos
    if not presupuestos.empty and not transacciones.empty:
        pdf.chapter_title('COMPARACION CON PRESUPUESTOS')
        gastos_cat = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum()
        presupuestos_dict = presupuestos.set_index('categoria')['monto_maximo'].to_dict()
        
        # Encabezados
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(50, 7, 'Categoria', 1, 0, 'C')
        pdf.cell(35, 7, 'Gasto Real', 1, 0, 'C')
        pdf.cell(35, 7, 'Presupuesto', 1, 0, 'C')
        pdf.cell(30, 7, '% Uso', 1, 0, 'C')
        pdf.cell(30, 7, 'Estado', 1, 1, 'C')
        
        for categoria in set(gastos_cat.index) & set(presupuestos_dict.keys()):
            gasto = gastos_cat[categoria]
            presupuesto = presupuestos_dict[categoria]
            cumplimiento = (gasto / presupuesto * 100) if presupuesto > 0 else 0
            estado = 'OK' if cumplimiento <= 100 else 'EXCEDIDO'
            
            pdf.set_font('Arial', '', 9)
            pdf.cell(50, 6, f'{categoria[:20]}', 1, 0)
            pdf.cell(35, 6, f'${gasto:,.2f}', 1, 0, 'R')
            pdf.cell(35, 6, f'${presupuesto:,.2f}', 1, 0, 'R')
            pdf.cell(30, 6, f'{cumplimiento:.1f}%', 1, 0, 'C')
            
            pdf.set_font('Arial', 'B', 9)
            if estado == 'EXCEDIDO':
                pdf.set_text_color(255, 0, 0)
            else:
                pdf.set_text_color(0, 128, 0)
            pdf.cell(30, 6, estado, 1, 1, 'C')
            pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
    
    # Recomendaciones de IA
    pdf.chapter_title('RECOMENDACIONES INTELIGENTES')
    for i, rec in enumerate(analisis['recomendaciones'], 1):
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 7, f'{i}. {rec}')
        pdf.ln(2)
    pdf.ln(3)
    
    # Alertas
    if analisis['alertas']:
        pdf.chapter_title('ALERTAS IMPORTANTES')
        for alerta in analisis['alertas']:
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(255, 102, 0)
            pdf.multi_cell(0, 7, f'! {alerta}')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
        pdf.ln(3)
    
    # Predicciones
    pdf.chapter_title('PROYECCIONES FINANCIERAS')
    pdf.add_metric('Ahorro proyectado (3 meses)', f"${analisis['predicciones']['ahorro_3_meses']:,.2f}")
    pdf.add_metric('Gastos del proximo mes', f"${analisis['predicciones']['proyeccion_gastos']:,.2f}")
    
    # Transacciones recientes
    if not transacciones.empty:
        pdf.add_page()
        pdf.chapter_title('TRANSACCIONES RECIENTES (ULTIMAS 20)')
        
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(25, 6, 'Fecha', 1, 0, 'C')
        pdf.cell(35, 6, 'Categoria', 1, 0, 'C')
        pdf.cell(75, 6, 'Descripcion', 1, 0, 'C')
        pdf.cell(30, 6, 'Monto', 1, 0, 'C')
        pdf.cell(20, 6, 'Tipo', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 7)
        transacciones_sorted = transacciones.sort_values('fecha', ascending=False).head(20)
        
        for _, row in transacciones_sorted.iterrows():
            pdf.cell(25, 5, str(row['fecha'])[:10], 1, 0)
            pdf.cell(35, 5, str(row['categoria'])[:15], 1, 0)
            pdf.cell(75, 5, str(row['descripcion'])[:35], 1, 0)
            pdf.cell(30, 5, f"${row['monto']:.2f}", 1, 0, 'R')
            pdf.cell(20, 5, str(row['tipo'])[:8], 1, 1, 'C')
    
    # FIX: Usar output() sin encode
    try:
        # Para fpdf2 (versión 2.x)
        pdf_output = pdf.output()
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin1')
        return pdf_output
    except:
        # Para fpdf (versión 1.x)
        return pdf.output(dest='S').encode('latin1')

# ==================== PÁGINAS ====================

def pagina_dashboard(db: DatabaseManager, usuario_mgr: UsuarioManager, 
                     transaccion_mgr: TransaccionManager, presupuesto_mgr: PresupuestoManager,
                     alerta_mgr: AlertaManager):
    """Página principal del dashboard financiero"""

    with st.sidebar:
        st.header("📊 Configuración")
        
        st.text(st.session_state['user_name'])
        usuario_nombre = st.session_state['user_name']
        usuario_id =st.session_state['user_id']
        
        periodo = st.selectbox("Período de análisis", ["Últimos 7 días", "Últimos 30 días", "Últimos 90 días"])
        dias_map = {"Últimos 7 días": 7, "Últimos 30 días": 30, "Últimos 90 días": 90}
        dias = dias_map[periodo]

        st.divider()
        mostrar_chat(usuario_id)

        st.markdown("---")
        st.header("⚡ Acciones Rápidas")
        if st.button("🔄 Actualizar Análisis", use_container_width=True):
            st.rerun()
        
        # Botón para generar PDF
        if st.button("📄 Generar Reporte PDF", use_container_width=True, type="primary"):
            with st.spinner('📄 Generando reporte PDF...'):
                try:
                    transacciones_pdf = transaccion_mgr.listar_transacciones(usuario_id, dias)
                    presupuestos_pdf = presupuesto_mgr.listar_presupuestos(usuario_id)
                    asesor_pdf = AsesorFinanciero(transaccion_mgr, presupuesto_mgr)
                    analisis_pdf = asesor_pdf.get_analisis_ia(transacciones_pdf, presupuestos_pdf)
                    
                    # Generar PDF
                    pdf_bytes = generar_reporte_pdf(
                        usuario_nombre, 
                        transacciones_pdf, 
                        analisis_pdf, 
                        presupuestos_pdf
                    )
                    
                    # Asegurar que sea bytes
                    if isinstance(pdf_bytes, bytearray):
                        pdf_bytes = bytes(pdf_bytes)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.success("✅ ¡Reporte PDF generado exitosamente!")
                    st.download_button(
                        label="📥 Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"reporte_financiero_{timestamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            
                except Exception as e:
                    st.error(f"❌ Error al generar PDF: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())


    st.title("💰 Dashboard Financiero")
    respuesta = "Aqui habra recomendaciones IA"
    recomendaciones = ""
    recomendaciones_alertas = ""

    # Obtener datos
    transacciones = transaccion_mgr.listar_transacciones(usuario_id, dias)
    presupuestos = presupuesto_mgr.listar_presupuestos(usuario_id)
    
    asesor = AsesorFinanciero(transaccion_mgr, presupuesto_mgr)
    analisis = asesor.get_analisis_ia(transacciones, presupuestos)

    if st.button('Recomendaciones IA'):
        try:
            response = requests.post(
                f"{asesor.n8n_webhook}/recomendacion-financiaunt",
                json={
                    'user_id': usuario_id,
                    'time': str(datetime.now())
                },
                timeout=250
            )
            if response.status_code == 200:
                data = response.json()
                recomendaciones = data.get('recomendaciones')
                recomendaciones_alertas = data.get('recomendaciones_alertas')
            else:
                respuesta = "❌ No pude procesar tu operación"
                    
        except requests.exceptions.Timeout:
            respuesta = "⏱️ Procesando en segundo plano..."
        except Exception as e:
            respuesta = f"❌ Error al conectar: {str(e)[:40]}"
            
    st.markdown("---")
    
    # Mostrar alertas del sistema como notificaciones temporales (10 segundos)
    df_alertas = alerta_mgr.listar_alertas(usuario_id, solo_no_leidas=True)
    if not df_alertas.empty:
        # Crear un contenedor para las alertas con auto-desaparición
        alerta_container = st.empty()
        
        with alerta_container.container():
            for idx, alerta in df_alertas.head(3).iterrows():
                if alerta['severidad'] == 'alta':
                    st.error(f"🔴 {alerta['mensaje']}", icon="🚨")
                elif alerta['severidad'] == 'media':
                    st.warning(f"🟡 {alerta['mensaje']}", icon="⚠️")
                else:
                    st.info(f"🟢 {alerta['mensaje']}", icon="ℹ️")
                
                # Auto-marcar como leída después de mostrar
                alerta_mgr.marcar_leida(alerta['id'])
        
        # JavaScript para ocultar las alertas después de 10 segundos
        st.markdown("""
        <script>
        setTimeout(function() {
            var alerts = document.querySelectorAll('[data-testid="stAlert"]');
            alerts.forEach(function(alert) {
                alert.style.transition = 'opacity 0.5s ease-out';
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.style.display = 'none';
                }, 500);
            });
        }, 10000);
        </script>
        """, unsafe_allow_html=True)
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💵 Ingresos Totales",
            f"${analisis['resumen']['total_ingresos']:,.2f}"
        )
    
    with col2:
        st.metric(
            "💸 Gastos Totales",
            f"${analisis['resumen']['total_gastos']:,.2f}",
            delta=f"-${analisis['resumen']['total_gastos']:,.2f}",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "💰 Ahorro Neto",
            f"${analisis['resumen']['ahorro_neto']:,.2f}",
            delta=f"{analisis['resumen']['tasa_ahorro']:.1f}%"
        )
    
    with col4:
        st.metric(
            "📈 Proyección 3 Meses",
            f"${analisis['predicciones']['ahorro_3_meses']:,.2f}",
            delta="+5%"
        )
    
    st.markdown("---")
    
    # Gráficos y análisis
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribución de Gastos")
        if not transacciones.empty:
            gastos_categoria = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum()
            if not gastos_categoria.empty:
                fig = px.pie(
                    values=gastos_categoria.values,
                    names=gastos_categoria.index,
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(showlegend=True, height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay gastos registrados")
        else:
            st.info("No hay transacciones en este período")
        
        # Tendencias
        st.subheader("📈 Tendencias de Gastos")
        if not transacciones.empty:
            transacciones['fecha'] = pd.to_datetime(transacciones['fecha'])
            gastos_diarios = transacciones[transacciones['tipo'] == 'gasto'].groupby('fecha')['monto'].sum().reset_index()
            
            if not gastos_diarios.empty:
                fig = px.line(
                    gastos_diarios,
                    x='fecha',
                    y='monto',
                    title='Evolución de Gastos Diarios'
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay gastos para mostrar tendencias")
        else:
            st.info("No hay datos de tendencias")
    
    with col2:
        st.subheader("🎯 Presupuesto vs Realidad")
        if not transacciones.empty and not presupuestos.empty:
            gastos_categoria = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum()
            presupuestos_dict = presupuestos.set_index('categoria')['monto_maximo'].to_dict()
            
            comparacion_data = []
            for cat in set(gastos_categoria.index) & set(presupuestos_dict.keys()):
                gasto_real = gastos_categoria.get(cat, 0)
                presupuesto = presupuestos_dict.get(cat, 0)
                comparacion_data.append({
                    'Categoría': cat,
                    'Gasto Real': gasto_real,
                    'Presupuesto': presupuesto,
                    'Diferencia': presupuesto - gasto_real
                })
            
            if comparacion_data:
                df_comparacion = pd.DataFrame(comparacion_data)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name='Gasto Real',
                    x=df_comparacion['Categoría'],
                    y=df_comparacion['Gasto Real'],
                    marker_color='#EF553B'
                ))
                fig.add_trace(go.Bar(
                    name='Presupuesto',
                    x=df_comparacion['Categoría'],
                    y=df_comparacion['Presupuesto'],
                    marker_color='#00CC96'
                ))
                
                fig.update_layout(barmode='group', height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay categorías comunes para comparar")
        else:
            st.info("Configura presupuestos para ver comparaciones")
        
        # Alertas y recomendaciones
        if recomendaciones != "":
            st.subheader("💡 Recomendaciones IA")
            st.info(recomendaciones)
        else:
            st.info(respuesta)
        
        if recomendaciones_alertas != "":
            st.subheader("⚠️ Recomendaciones Alertas IA")
            st.warning(recomendaciones_alertas)
    
    # Análisis detallado
    st.markdown("---")
    st.subheader("📋 Análisis Detallado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Transacciones Recientes**")
        if not transacciones.empty:
            st.dataframe(
                transacciones.sort_values('fecha', ascending=False).head(10)[
                    ['fecha', 'categoria', 'descripcion', 'monto', 'tipo']
                ],
                use_container_width=True
            )
        else:
            st.info("No hay transacciones")
    
    with col2:
        st.write("**Estadísticas Descriptivas**")
        if not transacciones.empty:
            gastos = transacciones[transacciones['tipo'] == 'gasto']['monto']
            stats_data = {
                'Métrica': [
                    'Total Transacciones',
                    'Promedio Gasto',
                    'Gasto Máximo',
                    'Gasto Mínimo',
                    'Desviación Estándar'
                ],
                'Valor': [
                    len(transacciones),
                    f"${gastos.mean():.2f}" if not gastos.empty else "$0.00",
                    f"${gastos.max():.2f}" if not gastos.empty else "$0.00",
                    f"${gastos.min():.2f}" if not gastos.empty else "$0.00",
                    f"${gastos.std():.2f}" if not gastos.empty else "$0.00"
                ]
            }
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True)
        else:
            st.info("No hay estadísticas")
    
    

    # Generar PDF si se solicitó
    if st.session_state.get('generar_pdf', False):
        with st.spinner('📄 Generando reporte PDF...'):
            try:
                pdf_bytes = generar_reporte_pdf(usuario_nombre, transacciones, analisis, presupuestos)
                
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="reporte_financiero_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf" style="display: inline-block; padding: 0.5rem 1rem; background-color: #FF4B4B; color: white; text-decoration: none; border-radius: 0.5rem; font-weight: bold;">📥 Descargar Reporte PDF</a>'
                
                st.success("✅ ¡Reporte PDF generado exitosamente!")
                st.markdown(href, unsafe_allow_html=True)
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error al generar PDF: {str(e)}")
            
            st.session_state['generar_pdf'] = False
class AsesorFinancieroAntiguo:
    def __init__(self):
        self.supabase_url = st.secrets.get("SUPABASE_URL", "https://tu-proyecto.supabase.co")
        self.supabase_key = st.secrets.get("SUPABASE_KEY", "tu-clave-supabase")
        self.n8n_webhook = st.secrets.get("N8N_WEBHOOK", "")
        
    def get_transacciones(self, usuario_id, dias=30):
        """Obtener transacciones de los últimos días"""
        # En producción, esto se conectaría a Supabase
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        # Datos de ejemplo
        categorias = ['Alimentación', 'Transporte', 'Entretenimiento', 'Servicios', 'Salud', 'Educación']
        transacciones = []
        
        # Si hay transacciones en la sesión, úsalas
        if 'transacciones' in st.session_state:
            return st.session_state.transacciones
        
        # Si no hay transacciones en la sesión, usa datos de ejemplo
        for i in range(100):
            fecha = fecha_inicio + timedelta(days=np.random.randint(0, dias))
            categoria = np.random.choice(categorias)
            monto = abs(np.random.normal(50, 30))
            
            transacciones.append({
                'id': f'trx_{i}',
                'usuario_id': usuario_id,
                'fecha': fecha.strftime('%Y-%m-%d'),
                'categoria': categoria,
                'descripcion': f'Compra en {categoria}',
                'monto': round(monto, 2),
                'tipo': 'gasto'
            })
        
        # Agregar algunos ingresos
        for i in range(10):
            fecha = fecha_inicio + timedelta(days=np.random.randint(0, dias))
            transacciones.append({
                'id': f'ing_{i}',
                'usuario_id': usuario_id,
                'fecha': fecha.strftime('%Y-%m-%d'),
                'categoria': 'Ingresos',
                'descripcion': 'Salario',
                'monto': round(np.random.normal(2000, 500), 2),
                'tipo': 'ingreso'
            })
        
        # Guardar en la sesión
        df = pd.DataFrame(transacciones)
        st.session_state.transacciones = df
        return df
        
    def agregar_gasto(self, usuario_id, monto, categoria, descripcion):
        """Agregar un nuevo gasto"""
        nueva_transaccion = {
            'id': f'trx_{int(datetime.time())}',
            'usuario_id': usuario_id,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'categoria': categoria,
            'descripcion': descripcion,
            'monto': float(monto),
            'tipo': 'gasto'
        }
        
        # Agregar a la sesión
        if 'transacciones' in st.session_state:
            df = st.session_state.transacciones
            df = pd.concat([df, pd.DataFrame([nueva_transaccion])], ignore_index=True)
            st.session_state.transacciones = df
        
        # En producción, aquí se haría la llamada a la API de n8n
        try:
            response = requests.post(
                self.n8n_webhook + "/webhook-expense",
                json={
                    'user_id': usuario_id,
                    'text': f"Agregar gasto de {monto} soles en {categoria} - {descripcion}"
                },
                timeout=5
            )
            return True, "Gasto agregado correctamente"
        except Exception as e:
            return False, f"Error al conectar con el servidor: {str(e)}"
    
    def get_presupuestos(self, usuario_id):
        """Obtener presupuestos del usuario"""
        presupuestos = {
            'Alimentación': 300,
            'Transporte': 200,
            'Entretenimiento': 150,
            'Servicios': 100,
            'Salud': 50,
            'Educación': 100
        }
        return presupuestos
    
    def get_analisis_ia(self, transacciones):
        """Generar análisis con IA (simulado)"""
        gastos_por_categoria = transacciones[transacciones['tipo'] == 'gasto'].groupby('categoria')['monto'].sum()
        total_gastos = gastos_por_categoria.sum()
        total_ingresos = transacciones[transacciones['tipo'] == 'ingreso']['monto'].sum()
        
        analisis = {
            'resumen': {
                'total_ingresos': total_ingresos,
                'total_gastos': total_gastos,
                'ahorro_neto': total_ingresos - total_gastos,
                'tasa_ahorro': ((total_ingresos - total_gastos) / total_ingresos * 100) if total_ingresos > 0 else 0
            },
            'recomendaciones': [
                "Considera reducir gastos en entretenimiento que superan el 15% de tus ingresos",
                "Podrías automatizar tus ahorros con un 20% de tu salario",
                "Revisa tus suscripciones recurrentes, algunas podrían no ser necesarias",
                "Excelente trabajo manteniendo tus gastos de alimentación dentro del presupuesto"
            ],
            'alertas': [
                "Gastos en transporte cerca de exceder el presupuesto",
                "Patrón de gastos los fines de semana superior al promedio"
            ],
            'predicciones': {
                'ahorro_3_meses': (total_ingresos - total_gastos) * 3 * 1.1,  # +10% de crecimiento
                'proyeccion_gastos': total_gastos * 1.05  # +5% de incremento
            }
        }
        
        return analisis

def mostrar_chat(usuario_id):
    """Chat simple y funcional con scroll que realmente funciona"""
    
    # Inicializar mensajes
    if 'mensajes' not in st.session_state:
        st.session_state.mensajes = [
            {
                "role": "assistant", 
                "content": "¡Hola! 👋 Soy tu asistente financiero.\n\nEjemplos:\n• Gasté 80 soles en supermercado y 20 en la escuela\n• Añade 50 de almuerzo hace dos dias, mi preupuesto para la semana es de 20 soles\n\nEn un mensaje puedes mandar varias operaciones para ingresos, gastos y presupuestos.\nRecuerda que funciona con IA por lo que debes verificar la información"
            }
        ]
    
    # CSS Simple pero efectivo
    st.markdown("""
        <style>
        .chat-box {
            background: #1e1e2e;
            border-radius: 12px;
            padding: 0;
            margin: 10px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            font-weight: 600;
            border-radius: 12px 12px 0 0;
            text-align: center;
        }
        
        .chat-msg-container {
            background: #252535;
            padding: 12px;
            height: 350px;
            overflow-y: scroll;
            overflow-x: hidden;
        }
        
        .chat-msg-container::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-msg-container::-webkit-scrollbar-track {
            background: #1e1e2e;
        }
        
        .chat-msg-container::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 3px;
        }
        
        .msg-assistant {
            background: #3a3a4a;
            color: #e8e8e8;
            padding: 10px 12px;
            border-radius: 12px;
            border-bottom-left-radius: 3px;
            margin: 8px 15% 8px 0;
            font-size: 13px;
            line-height: 1.5;
            max-width: 85%;
            word-wrap: break-word;
            word-break: break-word;
            overflow-wrap: break-word;
            white-space: pre-wrap;
        }
        
        .msg-user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 12px;
            border-radius: 12px;
            border-bottom-right-radius: 3px;
            margin: 8px 0 8px 15%;
            font-size: 13px;
            line-height: 1.5;
            text-align: right;
            max-width: 85%;
            word-wrap: break-word;
            word-break: break-word;
            overflow-wrap: break-word;
            white-space: pre-wrap;
            margin-left: auto;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Construir todo el chat como HTML
    chat_html = '<div class="chat-box">'
    chat_html += '<div class="chat-header">💬 Chat de Gastos</div>'
    chat_html += '<div class="chat-msg-container" id="chatMessages">'
    
    # Agregar todos los mensajes
    for mensaje in st.session_state.mensajes:
        contenido = mensaje["content"].replace("\n", "<br>")
        if mensaje["role"] == "assistant":
            chat_html += f'<div class="msg-assistant">{contenido}</div>'
        else:
            chat_html += f'<div class="msg-user">{contenido}</div>'
    
    chat_html += '</div></div>'
    
    # Renderizar el chat completo
    st.markdown(chat_html, unsafe_allow_html=True)
    
    # Auto-scroll
    st.markdown("""
        <script>
        setTimeout(function() {
            var container = parent.document.getElementById('chatMessages');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }, 100);
        </script>
    """, unsafe_allow_html=True)
    
    # Form para input (FUERA del chat HTML)
    with st.form(key=f"chat_form_{len(st.session_state.mensajes)}", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "msg",
                placeholder="Escribe tu gasto aquí...",
                label_visibility="collapsed"
            )
        
        with col2:
            enviar = st.form_submit_button("➤", use_container_width=True)
        
        if enviar and user_input.strip():
            # Agregar mensaje del usuario
            st.session_state.mensajes.append({
                "role": "user",
                "content": user_input.strip()
            })
            
            # Llamar al webhook
            asesor = AsesorFinancieroAntiguo()
            
            try:
                response = requests.post(
                    f"{asesor.n8n_webhook}/transaccion-financiaunt",
                    json={
                        'user_id': usuario_id,
                        'text': user_input.strip(),
                        'time': str(datetime.now())
                    },
                    timeout=250
                )
                if response.status_code == 200:
                    data = response.json()[0]['messages']
                    respuesta = f"Operaciones hechas"
                    for d in data:
                        respuesta += '\n- '+d
                else:
                    respuesta = "❌ No pude procesar tu operación"
                    
            except requests.exceptions.Timeout:
                respuesta = "⏱️ Procesando en segundo plano..."
            except Exception as e:
                respuesta = f"❌ Error al conectar: {str(e)[:40]}"
            
            # Agregar respuesta
            st.session_state.mensajes.append({
                "role": "assistant",
                "content": respuesta
            })
            print(respuesta)
            st.rerun()

def pagina_mantenedores(db: DatabaseManager, usuario_mgr: UsuarioManager, 
                        transaccion_mgr: TransaccionManager, presupuesto_mgr: PresupuestoManager,
                        alerta_mgr: AlertaManager):
    """Página de mantenedores"""
    st.title("⚙️ Sistema de Mantenedores")
    st.markdown("---")
    
    menu = st.sidebar.selectbox(
        "Seleccionar Mantenedor",
        ["👥 Usuarios", "💳 Transacciones", "🎯 Presupuestos", "⚠️ Alertas"]
    )
    
    # === MANTENEDOR DE USUARIOS ===
    if menu == "👥 Usuarios":
        st.header("Gestión de Usuarios")
        
        tab1, tab2, tab3 = st.tabs(["📋 Listar", "➕ Crear", "✏️ Editar/Eliminar"])
        
        with tab1:
            df_usuarios = usuario_mgr.listar_usuarios()
            if not df_usuarios.empty:
                st.dataframe(df_usuarios, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Usuarios", len(df_usuarios))
                with col2:
                    plan_counts = df_usuarios['plan_suscripcion'].value_counts()
                    st.metric("Plan Premium", plan_counts.get('premium', 0))
                with col3:
                    st.metric("Plan Básico", plan_counts.get('basico', 0))
            else:
                st.info("No hay usuarios registrados")
        
        with tab2:
            with st.form("form_crear_usuario"):
                st.subheader("Crear Nuevo Usuario")
                col1, col2 = st.columns(2)
                
                with col1:
                    email = st.text_input("Email*", placeholder="usuario@ejemplo.com")
                    nombre = st.text_input("Nombre*", placeholder="Juan Pérez")
                
                with col2:
                    plan = st.selectbox("Plan de Suscripción", ["basico", "premium", "enterprise"])
                
                submitted = st.form_submit_button("Crear Usuario", use_container_width=True)
                
                if submitted:
                    if email and nombre:
                        try:
                            resultado = usuario_mgr.crear_usuario(email, nombre, plan)
                            st.success(f"✅ Usuario creado: {resultado['nombre']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                    else:
                        st.warning("⚠️ Complete todos los campos obligatorios")
        
        with tab3:
            df_usuarios = usuario_mgr.listar_usuarios()
            if not df_usuarios.empty:
                usuario_seleccionado = st.selectbox(
                    "Seleccionar Usuario",
                    options=df_usuarios['id'].tolist(),
                    format_func=lambda x: df_usuarios[df_usuarios['id']==x]['nombre'].values[0]
                )
                
                if usuario_seleccionado:
                    usuario_data = df_usuarios[df_usuarios['id']==usuario_seleccionado].iloc[0]
                    
                    with st.form("form_editar_usuario"):
                        st.subheader("Editar Usuario")
                        
                        nuevo_nombre = st.text_input("Nombre", value=usuario_data['nombre'])
                        nuevo_email = st.text_input("Email", value=usuario_data['email'])
                        nuevo_plan = st.selectbox(
                            "Plan", 
                            ["basico", "premium", "enterprise"],
                            index=["basico", "premium", "enterprise"].index(usuario_data['plan_suscripcion'])
                        )
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            actualizar = st.form_submit_button("💾 Actualizar", use_container_width=True)
                        with col_b:
                            eliminar = st.form_submit_button("🗑️ Eliminar", use_container_width=True, type="secondary")
                        
                        if actualizar:
                            datos = {
                                'nombre': nuevo_nombre,
                                'email': nuevo_email,
                                'plan_suscripcion': nuevo_plan
                            }
                            usuario_mgr.actualizar_usuario(usuario_seleccionado, datos)
                            st.success("✅ Usuario actualizado")
                            st.rerun()
                        
                        if eliminar:
                            if st.session_state.get('confirmar_eliminar'):
                                usuario_mgr.eliminar_usuario(usuario_seleccionado)
                                st.success("✅ Usuario eliminado")
                                st.session_state.confirmar_eliminar = False
                                st.rerun()
                            else:
                                st.session_state.confirmar_eliminar = True
                                st.warning("⚠️ Presione nuevamente para confirmar")
    
    # === MANTENEDOR DE TRANSACCIONES ===
    elif menu == "💳 Transacciones":
        st.header("Gestión de Transacciones")
        
        df_usuarios = usuario_mgr.listar_usuarios()
        if df_usuarios.empty:
            st.warning("No hay usuarios registrados")
            return
        
        col1, col2 = st.columns(2)
        with col1:
            usuario_filtro = st.selectbox(
                "Filtrar por Usuario",
                options=['Todos'] + df_usuarios['id'].tolist(),
                format_func=lambda x: 'Todos' if x == 'Todos' else df_usuarios[df_usuarios['id']==x]['nombre'].values[0]
            )
        
        with col2:
            dias_filtro = st.selectbox("Período", [7, 30, 90, 365], index=1)
        
        tab1, tab2, tab3 = st.tabs(["📋 Listar", "➕ Crear", "✏️ Editar/Eliminar"])
        
        with tab1:
            usuario_id = None if usuario_filtro == 'Todos' else usuario_filtro
            df_transacciones = transaccion_mgr.listar_transacciones(usuario_id, dias_filtro)
            
            if not df_transacciones.empty:
                st.dataframe(df_transacciones, use_container_width=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Transacciones", len(df_transacciones))
                with col2:
                    ingresos = df_transacciones[df_transacciones['tipo']=='ingreso']['monto'].sum()
                    st.metric("Ingresos", f"${ingresos:,.2f}")
                with col3:
                    gastos = df_transacciones[df_transacciones['tipo']=='gasto']['monto'].sum()
                    st.metric("Gastos", f"${gastos:,.2f}")
                with col4:
                    st.metric("Balance", f"${ingresos-gastos:,.2f}")
            else:
                st.info("No hay transacciones en el período seleccionado")
        
        with tab2:
            with st.form("form_crear_transaccion"):
                st.subheader("Nueva Transacción")
                
                col1, col2 = st.columns(2)
                with col1:
                    usuario_trans = st.selectbox(
                        "Usuario*",
                        options=df_usuarios['id'].tolist(),
                        format_func=lambda x: df_usuarios[df_usuarios['id']==x]['nombre'].values[0]
                    )
                    monto = st.number_input("Monto*", min_value=0.01, step=0.01)
                    tipo = st.selectbox("Tipo*", ["gasto", "ingreso"])
                
                with col2:
                    categorias = ['Alimentación', 'Transporte', 'Entretenimiento', 'Servicios', 
                                 'Salud', 'Educación', 'Ingresos', 'Otros']
                    categoria = st.selectbox("Categoría*", categorias)
                    fecha = st.date_input("Fecha*", value=datetime.now())
                
                descripcion = st.text_area("Descripción*", placeholder="Detalle de la transacción")
                
                submitted = st.form_submit_button("Crear Transacción", use_container_width=True)
                
                if submitted:
                    if usuario_trans and monto and categoria and descripcion:
                        try:
                            transaccion_mgr.crear_transaccion(
                                usuario_trans, monto, categoria, descripcion, 
                                fecha.strftime('%Y-%m-%d'), tipo, ''
                            )
                            st.success("✅ Transacción creada correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                    else:
                        st.warning("⚠️ Complete todos los campos obligatorios")
        
        with tab3:
            df_trans_edit = transaccion_mgr.listar_transacciones(dias=30)
            if not df_trans_edit.empty:
                trans_seleccionada = st.selectbox(
                    "Seleccionar Transacción",
                    options=df_trans_edit['id'].tolist(),
                    format_func=lambda x: f"{df_trans_edit[df_trans_edit['id']==x]['descripcion'].values[0][:30]} - ${df_trans_edit[df_trans_edit['id']==x]['monto'].values[0]}"
                )
                
                if trans_seleccionada:
                    trans_data = df_trans_edit[df_trans_edit['id']==trans_seleccionada].iloc[0]
                    
                    with st.form("form_editar_transaccion"):
                        col1, col2 = st.columns(2)
                        with col1:
                            nuevo_monto = st.number_input("Monto", value=float(trans_data['monto']))
                            nueva_categoria = st.text_input("Categoría", value=trans_data['categoria'])
                        with col2:
                            nuevo_tipo = st.selectbox("Tipo", ["gasto", "ingreso"], 
                                                     index=0 if trans_data['tipo']=='gasto' else 1)
                            nueva_fecha = st.date_input("Fecha", value=pd.to_datetime(trans_data['fecha']))
                        
                        nueva_desc = st.text_area("Descripción", value=trans_data['descripcion'])
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            actualizar = st.form_submit_button("💾 Actualizar", use_container_width=True)
                        with col_b:
                            eliminar = st.form_submit_button("🗑️ Eliminar", use_container_width=True)
                        
                        if actualizar:
                            datos = {
                                'monto': nuevo_monto,
                                'categoria': nueva_categoria,
                                'tipo': nuevo_tipo,
                                'fecha': nueva_fecha.strftime('%Y-%m-%d'),
                                'descripcion': nueva_desc
                            }
                            transaccion_mgr.actualizar_transaccion(trans_seleccionada, datos)
                            st.success("✅ Transacción actualizada")
                            st.rerun()
                        
                        if eliminar:
                            transaccion_mgr.eliminar_transaccion(trans_seleccionada)
                            st.success("✅ Transacción eliminada")
                            st.rerun()
            else:
                st.info("No hay transacciones para editar")
    
    # === MANTENEDOR DE PRESUPUESTOS ===
    elif menu == "🎯 Presupuestos":
        st.header("Gestión de Presupuestos")
        
        tab1, tab2, tab3 = st.tabs(["📋 Listar", "➕ Crear", "✏️ Editar/Eliminar"])
        
        with tab1:
            df_presupuestos = presupuesto_mgr.listar_presupuestos()
            if not df_presupuestos.empty:
                st.dataframe(df_presupuestos, use_container_width=True)
                
                fig = px.bar(df_presupuestos, x='categoria', y='monto_maximo', 
                           title='Presupuestos por Categoría', color='periodo')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay presupuestos configurados")
        
        with tab2:
            df_usuarios = usuario_mgr.listar_usuarios()
            if not df_usuarios.empty:
                with st.form("form_crear_presupuesto"):
                    st.subheader("Nuevo Presupuesto")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        usuario_pres = st.selectbox(
                            "Usuario*",
                            options=df_usuarios['id'].tolist(),
                            format_func=lambda x: df_usuarios[df_usuarios['id']==x]['nombre'].values[0]
                        )
                        categoria_pres = st.selectbox("Categoría*", 
                            ['Alimentación', 'Transporte', 'Entretenimiento', 'Servicios', 
                             'Salud', 'Educación', 'Otros'])
                    
                    with col2:
                        monto_max = st.number_input("Monto Máximo*", min_value=0.01, step=10.0)
                        periodo_pres = st.selectbox("Período*", ['mensual', 'semanal', 'anual'])
                    
                    submitted = st.form_submit_button("Crear Presupuesto", use_container_width=True)
                    
                    if submitted:
                        try:
                            presupuesto_mgr.crear_presupuesto(
                                usuario_pres, categoria_pres, monto_max, periodo_pres
                            )
                            st.success("✅ Presupuesto creado")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("No hay usuarios registrados")
        
        with tab3:
            df_pres_edit = presupuesto_mgr.listar_presupuestos()
            if not df_pres_edit.empty:
                pres_seleccionado = st.selectbox(
                    "Seleccionar Presupuesto",
                    options=df_pres_edit['id'].tolist(),
                    format_func=lambda x: f"{df_pres_edit[df_pres_edit['id']==x]['categoria'].values[0]} - ${df_pres_edit[df_pres_edit['id']==x]['monto_maximo'].values[0]}"
                )
                
                if pres_seleccionado:
                    pres_data = df_pres_edit[df_pres_edit['id']==pres_seleccionado].iloc[0]
                    
                    with st.form("form_editar_presupuesto"):
                        col1, col2 = st.columns(2)
                        with col1:
                            nueva_categoria = st.text_input("Categoría", value=pres_data['categoria'])
                            nuevo_monto = st.number_input("Monto Máximo", value=float(pres_data['monto_maximo']))
                        with col2:
                            nuevo_periodo = st.selectbox("Período", 
                                ['mensual', 'semanal', 'anual'],
                                index=['mensual', 'semanal', 'anual'].index(pres_data['periodo']))
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            actualizar = st.form_submit_button("💾 Actualizar", use_container_width=True)
                        with col_b:
                            eliminar = st.form_submit_button("🗑️ Eliminar", use_container_width=True)
                        
                        if actualizar:
                            datos = {
                                'categoria': nueva_categoria,
                                'monto_maximo': nuevo_monto,
                                'periodo': nuevo_periodo
                            }
                            presupuesto_mgr.actualizar_presupuesto(pres_seleccionado, datos)
                            st.success("✅ Presupuesto actualizado")
                            st.rerun()
                        
                        if eliminar:
                            presupuesto_mgr.eliminar_presupuesto(pres_seleccionado)
                            st.success("✅ Presupuesto eliminado")
                            st.rerun()
    
    # === MANTENEDOR DE ALERTAS ===
    elif menu == "⚠️ Alertas":
        st.header("Gestión de Alertas")
        
        tab1, tab2 = st.tabs(["📋 Listar", "➕ Crear"])
        
        with tab1:
            solo_no_leidas = st.checkbox("Solo alertas no leídas")
            
            df_alertas = alerta_mgr.listar_alertas(solo_no_leidas=solo_no_leidas)
            
            if not df_alertas.empty:
                for idx, alerta in df_alertas.iterrows():
                    severidad_icon = {"baja": "🟢", "media": "🟡", "alta": "🔴"}
                    icon = severidad_icon.get(alerta['severidad'], "⚪")
                    
                    with st.expander(f"{icon} {alerta['tipo']} - {alerta['mensaje'][:50]}..."):
                        st.write(f"**Mensaje:** {alerta['mensaje']}")
                        st.write(f"**Severidad:** {alerta['severidad']}")
                        st.write(f"**Fecha:** {alerta['created_at']}")
                        st.write(f"**Estado:** {'✅ Leída' if alerta['leida'] else '⏳ No leída'}")
                        
                        if not alerta['leida']:
                            if st.button(f"Marcar como leída", key=f"leer_{alerta['id']}"):
                                alerta_mgr.marcar_leida(alerta['id'])
                                st.success("✅ Alerta marcada como leída")
                                st.rerun()
            else:
                st.info("No hay alertas para mostrar")
        
        with tab2:
            df_usuarios = usuario_mgr.listar_usuarios()
            if not df_usuarios.empty:
                with st.form("form_crear_alerta"):
                    st.subheader("Nueva Alerta")
                    
                    usuario_alerta = st.selectbox(
                        "Usuario*",
                        options=df_usuarios['id'].tolist(),
                        format_func=lambda x: df_usuarios[df_usuarios['id']==x]['nombre'].values[0]
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        tipo_alerta = st.selectbox("Tipo*", 
                            ['presupuesto_excedido', 'gasto_inusual', 'recordatorio', 'sugerencia'])
                    with col2:
                        severidad_alerta = st.selectbox("Severidad*", ['baja', 'media', 'alta'])
                    
                    mensaje_alerta = st.text_area("Mensaje*", placeholder="Descripción de la alerta")
                    
                    submitted = st.form_submit_button("Crear Alerta", use_container_width=True)
                    
                    if submitted:
                        if mensaje_alerta:
                            try:
                                alerta_mgr.crear_alerta(
                                    usuario_alerta, tipo_alerta, mensaje_alerta, severidad_alerta
                                )
                                st.success("✅ Alerta creada")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                        else:
                            st.warning("⚠️ Complete el mensaje de la alerta")
            else:
                st.warning("No hay usuarios registrados")

# ==================== MAIN ====================

def main():
    # Inicializar managers
    db = DatabaseManager()
    
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:

        menu = st.sidebar.radio('Ingreso al sistema',['Autentificación'])

        if menu == 'Autentificación':
            main_auth()
        return
    
    else:


        if db.client is None:
            st.error("❌ No se pudo conectar a la base de datos. Verifica las credenciales en secrets.")
            return
        
        usuario_mgr = UsuarioManager(db)
        transaccion_mgr = TransaccionManager(db)
        presupuesto_mgr = PresupuestoManager(db)
        alerta_mgr = AlertaManager(db)
        
        # Menú principal en sidebar
        st.sidebar.title("🏦 Asesor Financiero IA")
        
        pagina = st.sidebar.radio(
            "Navegación",
            ["📊 Dashboard", "⚙️ Mantenedores"],
            label_visibility="collapsed"
        )
        
        # Renderizar página seleccionada
        if pagina == "📊 Dashboard":
            pagina_dashboard(db, usuario_mgr, transaccion_mgr, presupuesto_mgr, alerta_mgr)
        else:
            pagina_mantenedores(db, usuario_mgr, transaccion_mgr, presupuesto_mgr, alerta_mgr)

if __name__ == "__main__":
    main()



