import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import os

def get_db_connection():
    conn = sqlite3.connect('outfit_calculator.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS materials
                 (id INTEGER PRIMARY KEY, 
                  material TEXT, 
                  average_price REAL, 
                  waste_percentage REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS accessories
                 (id INTEGER PRIMARY KEY, 
                  accessory TEXT, 
                  price REAL)''')
    conn.commit()
    conn.close()

def load_data(table_name):
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def save_data(data, table_name):
    conn = get_db_connection()
    data.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    st.success(f'Daten in {table_name} gespeichert!')

init_db()

materials_db = load_data('materials')
accessories_db = load_data('accessories')

if materials_db.empty:
    materials_db = pd.DataFrame({
        'material': ['Baumwolle', 'Seide', 'Leinen'],
        'average_price': [10, 30, 20],
        'waste_percentage': [10, 15, 12]
    })
    save_data(materials_db, 'materials')

if accessories_db.empty:
    accessories_db = pd.DataFrame({
        'accessory': ['Knöpfe', 'Reißverschluss', 'Gürtel'],
        'price': [0.5, 2, 5]
    })
    save_data(accessories_db, 'accessories')

st.title('Outfit-Preis-Kalkulator')

tab1, tab2, tab3, tab4 = st.tabs(["Kalkulator", "Materialien verwalten", "Zubehör verwalten", "Hilfe"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        hourly_rate = st.number_input('Stundensatz (€)', min_value=0.0, value=50.0, step=0.5)
        fixed_costs = st.number_input('Fixkosten (€)', min_value=0.0, value=1500.0, step=10.0)
    with col2:
        outfits_per_month = st.number_input('Outfits pro Monat', min_value=1, value=3, step=1)
        consultation_hours = st.number_input('Beratungsstunden', min_value=0.0, value=2.0, step=0.5)

    profit_margin = st.slider('Gewinnmarge (%)', min_value=0, max_value=100, value=20, step=5)

    overhead_costs = fixed_costs / outfits_per_month
    consultation_costs = consultation_hours * hourly_rate
    st.write(f'Gemeinkosten pro Outfit: {overhead_costs:.2f} €')
    st.write(f'Beratungskosten: {consultation_costs:.2f} €')
    st.divider()

    all_possible_components = ['Kleid', 'Jacke', 'Oberteil', 'Hose', 'Rock', 'Overall']

    st.subheader('Outfit-Komponenten')
    components = [component for component in all_possible_components if st.checkbox(component)]

    total_cost = overhead_costs + consultation_costs

    component_costs = {component: {'Materialien': {}, 'Zubehör': {}, 'Arbeitskosten': 0} for component in all_possible_components}

    for component in components:
        with st.expander(f'{component} Details', expanded=True):
            work_hours = st.number_input(f'Arbeitszeit für {component} (Stunden)', min_value=0.0, key=f'{component}_hours', step=0.5)
            labor_cost = work_hours * hourly_rate
            total_cost += labor_cost
            component_costs[component]['Arbeitskosten'] = labor_cost
            st.write(f'Arbeitskosten: {labor_cost:.2f} €')
            
            material_tab, accessory_tab, cost_breakdown_tab = st.tabs(["Materialien", "Zubehör", "Kostenaufschlüsselung"])
            
            with material_tab:
                material_count = st.session_state.get(f'{component}_material_count', 1)
                for i in range(material_count):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        material = st.selectbox('Material', options=[''] + materials_db['material'].tolist(), key=f'{component}_material_{i}')
                    with col2:
                        amount = st.number_input('Menge (m)', min_value=0.0, key=f'{component}_material_amount_{i}', step=0.5)
                    with col3:
                        if material:
                            material_data = materials_db[materials_db['material'] == material].iloc[0]
                            material_price = float(material_data['average_price'])
                            material_waste = float(material_data['waste_percentage']) / 100
                            material_cost = amount * material_price * (1 + material_waste)
                            total_cost += material_cost
                            component_costs[component]['Materialien'][material] = material_cost
                            st.markdown(f'<div style="text-align: right;">{material_cost:.2f} €</div>', unsafe_allow_html=True)
                    with col4:
                        if st.button('X', key=f'{component}_remove_material_{i}'):
                            del st.session_state[f'{component}_material_{i}']
                            del st.session_state[f'{component}_material_amount_{i}']
                            st.session_state[f'{component}_material_count'] = material_count - 1
                            st.rerun()
                if st.button('Material hinzufügen', key=f'{component}_add_material'):
                    st.session_state[f'{component}_material_count'] = material_count + 1
                    st.rerun()

            with accessory_tab:
                accessory_count = st.session_state.get(f'{component}_accessory_count', 1)
                for i in range(accessory_count):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        accessory = st.selectbox('Zubehör', options=[''] + accessories_db['accessory'].tolist(), key=f'{component}_accessory_{i}')
                    with col2:
                        amount = st.number_input('Menge', min_value=0, key=f'{component}_accessory_amount_{i}', step=1)
                    with col3:
                        if accessory:
                            accessory_data = accessories_db[accessories_db['accessory'] == accessory].iloc[0]
                            accessory_price = float(accessory_data['price'])
                            accessory_cost = amount * accessory_price
                            total_cost += accessory_cost
                            component_costs[component]['Zubehör'][accessory] = accessory_cost
                            st.markdown(f'<div style="text-align: right;">{accessory_cost:.2f} €</div>', unsafe_allow_html=True)
                    with col4:
                        if st.button('X', key=f'{component}_remove_accessory_{i}'):
                            del st.session_state[f'{component}_accessory_{i}']
                            del st.session_state[f'{component}_accessory_amount_{i}']
                            st.session_state[f'{component}_accessory_count'] = accessory_count - 1
                            st.rerun()
                if st.button('Zubehör hinzufügen', key=f'{component}_add_accessory'):
                    st.session_state[f'{component}_accessory_count'] = accessory_count + 1
                    st.rerun()

            with cost_breakdown_tab:
                st.subheader('Kostenaufschlüsselung')
                st.write('Materialien:')
                for material, cost in component_costs[component]['Materialien'].items():
                    st.write(f'- {material}: {cost:.2f} €')
                st.write('Zubehör:')
                for accessory, cost in component_costs[component]['Zubehör'].items():
                    st.write(f'- {accessory}: {cost:.2f} €')
                st.write(f'Arbeitskosten: {component_costs[component]["Arbeitskosten"]:.2f} €')
                component_total = sum(component_costs[component]['Materialien'].values()) + sum(component_costs[component]['Zubehör'].values()) + component_costs[component]['Arbeitskosten']
                st.write(f'Gesamtkosten für {component}: {component_total:.2f} €')    

    st.divider()
    st.subheader('Gesamtübersicht')

    total_material_cost = sum(cost for component in components for cost in component_costs[component]['Materialien'].values())
    total_accessory_cost = sum(cost for component in components for cost in component_costs[component]['Zubehör'].values())
    total_labor_cost = sum(component_costs[component]['Arbeitskosten'] for component in components)

    production_cost = total_material_cost + total_accessory_cost + total_labor_cost + overhead_costs + consultation_costs

    profit_amount = production_cost * (profit_margin / 100)
    final_price = production_cost + profit_amount

    total_df = pd.DataFrame({
        'Komponente': components + ['Beratung', 'Gemeinkosten'],
        'Materialkosten': [sum(component_costs[c]['Materialien'].values()) for c in components] + [0, 0],
        'Zubehörkosten': [sum(component_costs[c]['Zubehör'].values()) for c in components] + [0, 0],
        'Arbeitskosten': [component_costs[c]['Arbeitskosten'] for c in components] + [consultation_costs, overhead_costs],
        'Gesamtkosten': [sum(component_costs[c]['Materialien'].values()) + 
                         sum(component_costs[c]['Zubehör'].values()) + 
                         component_costs[c]['Arbeitskosten'] for c in components] + [consultation_costs, overhead_costs]
    })

    total_df['Materialkosten'] = total_df['Materialkosten'].apply(lambda x: f"{x:.2f} €")
    total_df['Zubehörkosten'] = total_df['Zubehörkosten'].apply(lambda x: f"{x:.2f} €")
    total_df['Arbeitskosten'] = total_df['Arbeitskosten'].apply(lambda x: f"{x:.2f} €")
    total_df['Gesamtkosten'] = total_df['Gesamtkosten'].apply(lambda x: f"{x:.2f} €")

    st.dataframe(total_df, hide_index=True)

    st.write(f"Gesamtproduktionskosten: {production_cost:.2f} €")
    st.write(f"Gewinnbetrag: {profit_amount:.2f} €")
    st.write(f"Empfohlener Verkaufspreis: {final_price:.2f} €")

    fig, ax = plt.subplots()
    costs = [total_material_cost, total_accessory_cost, total_labor_cost, overhead_costs, consultation_costs]
    labels = ['Materialien', 'Zubehör', 'Arbeitskosten', 'Gemeinkosten', 'Beratung']
    ax.pie(costs, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

with tab2:
    st.subheader('Materialien verwalten')
    
    edited_materials = st.data_editor(materials_db, num_rows="dynamic")
    
    if st.button('Änderungen an Materialien speichern'):
        save_data(edited_materials, 'materials')
        materials_db = edited_materials

with tab3:
    st.subheader('Zubehör verwalten')
    
    edited_accessories = st.data_editor(accessories_db, num_rows="dynamic")
    
    if st.button('Änderungen an Zubehör speichern'):
        save_data(edited_accessories, 'accessories')
        accessories_db = edited_accessories

with tab4:
    st.subheader('Hilfe')
    st.write("""
    Willkommen beim Outfit-Preis-Kalkulator!

    So verwenden Sie diese App:

    1. Im 'Kalkulator' Tab:
       - Geben Sie die grundlegenden Informationen ein (Stundensatz, Fixkosten, etc.).
       - Wählen Sie die Outfit-Komponenten aus.
       - Fügen Sie für jede Komponente Materialien und Zubehör hinzu.
       - Sehen Sie sich die Gesamtübersicht und Kostenverteilung an.

    2. Im 'Materialien verwalten' Tab:
       - Fügen Sie neue Materialien hinzu, bearbeiten oder löschen Sie bestehende.
       - Klicken Sie auf 'Änderungen speichern', um Ihre Änderungen zu sichern.

    3. Im 'Zubehör verwalten' Tab:
       - Fügen Sie neues Zubehör hinzu, bearbeiten oder löschen Sie bestehendes.
       - Klicken Sie auf 'Änderungen speichern', um Ihre Änderungen zu sichern.

    Alle Änderungen werden automatisch in der Datenbank gespeichert und stehen allen Benutzern zur Verfügung.

    Bei Fragen oder Problemen wenden Sie sich bitte an den Support.
    """)

if st.button('Kalkulation exportieren'):
    st.write('Exportfunktion noch nicht implementiert.')