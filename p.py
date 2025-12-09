from app import DatabaseManager, UsuarioManager
import streamlit as st
from auth import main_auth

db = DatabaseManager()
um = UsuarioManager(db)

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:

    main_auth()
    
else:

    st.title(um.listar_usuarios())
    print(um.listar_usuarios())