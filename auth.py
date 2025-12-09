import streamlit as st
from init_database import DatabaseInitializer

def main_auth():
    db = DatabaseInitializer()

    st.header('Ingreso al Sistema Financiero')
    tab1, tab2 = st.tabs(['LOGIN','REGISTRO'])

    with tab1:
        with st.form('login_usuario'):
            nombre = st.text_input('Ingrese nombre',key='login_nombre')
            contraseña = st.text_input('Ingrese contraseña',key='login_contraseña',type='password')
            usuario = {
                'nombre':nombre,
                'access_token_plaid':contraseña
            }
            submited = st.form_submit_button('Ingresar')
            try:
                if submited:
                    if nombre and contraseña:
                        if db.login(usuario):
                            st.session_state['logged_in'] = True
                            st.rerun()
                    else:
                        st.error('Llena todos los campos')
            except Exception as e:
                st.error(f'Error: {e}')
    with tab2:
        nombre = st.text_input('Ingrese nombre',key='registro_nombre')
        contraseña = st.text_input('Ingrese contraseña',key='registro_contraseña',type='password')
        contraseña_r = st.text_input('Repita contraseña',type='password')
        correo = st.text_input('Ingrese correo')
        plan = st.selectbox('Seleccione un plan',options=['basico','premium','enterprise'])
        usuario = {
            'nombre':nombre,
            'access_token_plaid':contraseña,
            'email':correo,
            'plan_suscripcion':plan
        }
        if st.button('Registrar'):
            if nombre and contraseña and contraseña == contraseña_r:
                db.register(usuario)
            elif contraseña != contraseña_r:
                st.error('Contraseñas no coinciden')
            else:
                st.error('Llena todos los campos')

    st.info('Los datos son almacenados en supabase, no es necesario que ingrese datos reales')
            



