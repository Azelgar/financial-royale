import streamlit as st
import json
import os
import sys
import random
import psycopg2
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), 'engine'))
from engine import Engine

with open("config.json") as f:
    config = json.load(f)

engine = Engine(config)

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

# Ejecutar schema
with open("database/schema.sql") as f:
    cursor.execute(f.read())

st.title("Financial Royale MVP v2.1")

menu = st.sidebar.selectbox("Menú", ["Crear Cohorte", "Crear Jugador", "Jugar Semana", "Ranking"])

# =============================
# CREAR COHORTE
# =============================
if menu == "Crear Cohorte":
    name = st.text_input("Nombre cohorte")
    if st.button("Crear"):
        shock_week = random.randint(config["shock_week_min"], config["shock_week_max"])
        severity = random.choice([
            config["shock_sev_low"],
            config["shock_sev_mid"],
            config["shock_sev_high"]
        ])
        cursor.execute(
            "INSERT INTO cohorts (name, shock_week, shock_severity) VALUES (%s, %s, %s)",
            (name, shock_week, severity)
        )
        st.success("Cohorte creada")

# =============================
# CREAR JUGADOR
# =============================
elif menu == "Crear Jugador":

    cursor.execute("SELECT id, name FROM cohorts")
    cohorts = cursor.fetchall()

    if not cohorts:
        st.warning("Primero crea una cohorte.")
    else:
        cohort_dict = {c[1]: c[0] for c in cohorts}
        selected = st.selectbox("Seleccionar cohorte", list(cohort_dict.keys()))
        name = st.text_input("Nombre jugador")

        if st.button("Registrar"):
            cursor.execute(
                "INSERT INTO players (name, cohort_id, capital) VALUES (%s, %s, %s)",
                (name, cohort_dict[selected], config["capital_inicial"])
            )
            st.success("Jugador registrado")

# =============================
# JUGAR SEMANA
# =============================
elif menu == "Jugar Semana":

    cursor.execute("SELECT id, name, cohort_id FROM players")
    players = cursor.fetchall()

    if not players:
        st.warning("No hay jugadores.")
    else:
        player_dict = {f"{p[1]} (ID {p[0]})": p for p in players}
        selected = st.selectbox("Seleccionar jugador", list(player_dict.keys()))
        player_id, name, cohort_id = player_dict[selected]

        L = st.slider("Apalancamiento", 1.0, 3.0, 2.0)
        coverage = st.slider("Cobertura", 0.0, 1.0, 0.3)

        cursor.execute(
            "SELECT capital, week FROM players WHERE id=%s",
            (player_id,)
        )
        player = cursor.fetchone()
        capital, week = player

        if week > config["max_weeks"]:
            st.warning("Jugador ya completó las 10 semanas.")
        else:
            if st.button("Ejecutar"):

                r = engine.generate_return()
                adj_r = engine.adjusted_return(L, r)
                exposure = L * 0.6

                cursor.execute(
                    "SELECT shock_week, shock_severity FROM cohorts WHERE id=%s",

