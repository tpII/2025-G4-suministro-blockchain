# app/routes.py

from datetime import datetime
import json
import os
from app.config_loader import load_wine_config, save_wine_config
from flask import render_template, flash, redirect, url_for, request, Response, session
# Importa instancia de app y db
from app import app, db
# Importar clases de formulario
from app.forms import CreateAssetForm, LoginForm, ReadAssetForm, RegistrationForm, TransferAssetForm, UpdateAssetForm, NewVarietalForm, EditVarietalForm
#from app.config import WINE_VARIETALS
from app.config_loader import load_wine_config

# Manejo de usuarios
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
# Manejo de URLs
from werkzeug.urls import url_parse

# Manejo de peticiones
import requests
import time
import csv 
from io import StringIO, BytesIO

# Obtener organización segun el rol
def get_org():
    if current_user.is_authenticated:
        if current_user.role == "Productor":            
            return "Org1MSP"
        elif current_user.role == "Transportador":
            return "Org2MSP"
        else:
            return "Org3MSP"

# Obtener API_KEY segun el rol
def get_api_key():
    if current_user.is_authenticated:
        if current_user.role == "Productor":
            print(os.environ.get('API_KEY_PRODUCTOR'))
            return str(os.environ.get('API_KEY_PRODUCTOR'))
        elif current_user.role == "Transportador":
            return str(os.environ.get('API_KEY_TRANSPORTADOR'))
        else:
           return str(os.environ.get('API_KEY_CLIENTE'))
    else:
       return str(os.environ.get('API_KEY_CLIENTE'))
        

# Indice
from datetime import datetime
import json


@app.route('/index')
@login_required 
def index():
    headers = {"X-api-key": get_api_key()}
    API_BASE = os.environ.get('API_ADDRESS')
    
    assets = []
    all_history_events = []
    
    # --- PASO 1: Obtener todos los assets ---
    try:
        url_assets = f"{API_BASE}/api/assets"
        response_assets = requests.get(url_assets, headers=headers, timeout=10)
        response_assets.raise_for_status()
        assets_raw = response_assets.json()
        
        asset_ids = []
        for asset in assets_raw:
            asset_ids.append(asset.get('ID'))
            # Formateo de Owner
            if asset.get('Owner') == "Org1MSP": asset['Owner_Name'] = "Productor"
            elif asset.get('Owner') == "Org2MSP": asset['Owner_Name'] = "Transportador"
            elif asset.get('Owner') == "Org3MSP": asset['Owner_Name'] = "Cliente"
            assets.append(asset)

    except requests.exceptions.RequestException as e:
        flash(f"Error al cargar la lista de activos: {e}", "error")
        return render_template("index.html", assets=[], recent_activity=[])

    # --- PASO 2: Obtener historial de cada asset ---
    for asset_id in asset_ids:
        try:
            url_history = f"{API_BASE}/api/assets/history/{asset_id}"
            response_history = requests.get(url_history, headers=headers, timeout=10)
            response_history.raise_for_status()
            
            history_data = response_history.json()
            for event in history_data:
                event['asset_id'] = asset_id
                all_history_events.append(event)

        except requests.exceptions.RequestException as e:
            print(f"Advertencia: No se pudo obtener historial para ID {asset_id}. Error: {e}")

    # --- Función para convertir timestamp ---
    def get_timestamp_value(entry):
        seconds = entry.get('timestamp', {}).get('seconds', 0)
        nanos = entry.get('timestamp', {}).get('nanos', 0)
        return seconds + nanos / 1e9

    # --- PASO 3: Detectar cambios reales ---
    last_state_per_asset = {}
    all_changes = []

    # Orden ascendente para detectar creación primero
    all_history_events.sort(key=get_timestamp_value)

    for entry in all_history_events:
        asset_id = entry.get('asset_id')
        if entry.get('data'):
            try:
                print("DEBUG entry['data']:", entry.get('data'))
                data_dict = json.loads(entry['data'])
            except json.JSONDecodeError:
                #flash("Error: los datos recibidos no son JSON válido.", "error")
                data_dict = {}
        else:
            data_dict = {}
        timestamp = datetime.fromtimestamp(get_timestamp_value(entry))

        # Mapear Owner
        owner = data_dict.get('Owner', 'N/A')
        if owner == "Org1MSP": owner_name = "Productor"
        elif owner == "Org2MSP": owner_name = "Transportador"
        elif owner == "Org3MSP": owner_name = "Cliente"
        else: owner_name = "Desconocido"

        changes = []

        if asset_id not in last_state_per_asset:
            changes.append(f"Se creó el activo {data_dict.get('Varietal')} ({data_dict.get('ID')}) bajo la propiedad de {owner_name}.")
            operacion = "creacion"
        else:
            previous = last_state_per_asset[asset_id]
            
            # Detectar cambio de propietario
            if previous.get('Owner') != data_dict.get('Owner'):
                prev_owner = previous.get('Owner')
                if prev_owner == "Org1MSP": prev_owner_name = "Productor"
                elif prev_owner == "Org2MSP": prev_owner_name = "Transportador"
                elif prev_owner == "Org3MSP": prev_owner_name = "Cliente"
                else: prev_owner_name = "Desconocido"
                changes.append(
                    f"El activo {data_dict.get('Varietal')} ({data_dict.get('ID')}) fue transferido de {prev_owner_name} a {owner_name}."
                )
                operacion = "transferencia"
            
            # Detectar cambios en otros campos
            modificado = False
            for key, value in data_dict.items():
                if key != 'Owner' and previous.get(key) != value:
                    modificado = True

            if modificado:
                changes.append(
                    f"El activo {data_dict.get('Varietal')} ({data_dict.get('ID')}) fue modificado."
                )
                operacion = "modificacion"

        # Guardar el estado actual como último conocido
        last_state_per_asset[asset_id] = data_dict

        all_changes.append({
            'id': asset_id,
            'owner': owner_name,
            'timestamp_human': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'changes': changes,
            'data': data_dict,
            'operacion': operacion
        })

    # Tomar solo los últimos 5 cambios
    recent_activity_detailed = all_changes[-5:][::-1]

    # --- PASO 4: Estadísticas ---
    producer_assets = [a for a in assets if a['Owner'] == 'Org1MSP']
    transporter_assets = [a for a in assets if a['Owner'] == 'Org2MSP']
    client_assets = [a for a in assets if a['Owner'] == 'Org3MSP']

    stats = {
        'total_assets': len(assets),
        'total_wineries': len(set(a['Winery'] for a in assets)),
        'producer_in_production': len(producer_assets),
        'transporter_in_transit': len(transporter_assets),
        'transporter_temp_avg': round(
            sum(float(a.get('Temperature',0)) for a in transporter_assets) / len(transporter_assets), 1
        ) if transporter_assets else None,
        'client_received': len(client_assets),
        'client_price_avg': round(
            sum(float(a.get('Price',0)) for a in client_assets) / len(client_assets), 1
        ) if client_assets else None,
        'client_varieties': len(set(a['Varietal'] for a in client_assets))
    }

    return render_template(
        "index.html",
        assets=assets,
        recent_activity_detailed=recent_activity_detailed,
        stats=stats
    )

# Iniciar sesión
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    # Si se presiona el botón de cliente, salteamos validación
    if request.method == 'POST' and 'client_login' in request.form:
        client_user = User.query.filter_by(username='cliente').first()
        if not client_user:
            client_user = User(username='cliente')
            client_user.set_password('cliente')
            client_user.role = "Cliente"
            db.session.add(client_user)
            db.session.commit()
        
        login_user(client_user)
        return redirect(url_for('index'))

    # Solo validamos si es el botón normal de login
    if form.validate_on_submit() and 'submit' in request.form:
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'error')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)

    return render_template('login.html', title='Login', form=form)

# Cerrar sesión
@app.route('/logout')
def logout():
    logout_user()
    flash('Usted ha cerrado la sesión', 'success')  
    return redirect(url_for('login'))

# Registro de usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    # Si el formulario es valido
    if form.validate_on_submit():
        # Se instancia un usuario
        user = User(username=form.username.data)
        # Se genera una contraseña
        user.set_password(form.password.data)
        # Se agrega el rol
        user.role = form.role.data
        # Se agrega a la DB
        db.session.add(user)
        db.session.commit()
        # Mensaje de exito
        flash('El registro fue exitoso!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# Creacion/Actualización/Lectura

def handle_success(response):
    respuesta_api = response.json()
    flash(f"Respuesta de la API: {respuesta_api}", 'success')

def handle_job_created(response, headers):
    job_id = response.json()['jobId']
    url_job = f"{os.environ.get('API_ADDRESS')}/api/jobs/{job_id}"
    for _ in range(10):  # 10 intentos
        job_resp = requests.get(url_job, headers=headers).json()
        if 'transactionError' in job_resp:
            flash(f"Error en la solicitud: {job_resp['transactionError']}", 'error')
            break
        if job_resp.get('status') == 'completed':
            break
        time.sleep(0.2)  # 0.5 segundos entre intentos

def handle_error(response):
    if response.status_code == 401:
        flash("Error: No autorizado. Se requiere autenticación.", 'error')
    elif response.status_code == 403:
        flash("Error: Prohibido. No tienes permisos para acceder a este recurso.", 'error')
    elif response.status_code == 404:
        flash("Error: Recurso no encontrado.", 'error')
    else:
        flash(f"Error en la solicitud. Código: {response.status_code}", 'error')


@app.route("/read_asset", methods=['GET', 'POST'])
def read_asset():
    form = ReadAssetForm()
    if request.method == 'POST' and form.enviar_boton.data and form.validate_on_submit():
        rfid_value = form.rfid_tag.data

        url = f"{os.environ.get('API_ADDRESS')}/api/assets/{rfid_value}"
        headers = {
            "X-api-key": get_api_key(),
        }
        
        try:
            response = requests.get(url, headers=headers)

            if response is None:
                raise requests.RequestException("No se recibió respuesta.")

            if response.status_code == 200:
                    respuesta_api = response.json()
                    flash(f"Respuesta de la API: {respuesta_api}", 'success')
                    if respuesta_api['Owner']  == "Org1MSP":
                        respuesta_api['Owner'] = "Productor"
                    elif respuesta_api['Owner'] == "Org2MSP":
                        respuesta_api['Owner'] = "Transportador"
                    elif respuesta_api['Owner'] == "Org3MSP":
                        respuesta_api['Owner'] = "Cliente"
                    coordenadas = []
                    coordenadas.append({'latitude': respuesta_api['Latitude'], 'longitude': respuesta_api['Longitude']})
                    return render_template('read_asset.html', form=form, respuesta_api=respuesta_api, coordenadas=coordenadas)
            else:
                handle_error(response)
                return render_template('read_asset.html', title="Read",form=form)

        except requests.RequestException as e:
            flash(f"Error en la solicitud: {e}", 'error')
    
    return render_template('read_asset.html', form=form)

HUM_MIN, HUM_MAX = 60, 80

@app.route("/new_asset", methods=['GET', 'POST'])
def new_asset():
    form = CreateAssetForm()
    config = load_wine_config()
    WINE_VARIETALS = config["WINE_VARIETALS"]

    if request.method == 'POST' and form.enviar_boton.data and form.validate_on_submit():
        rfid_value = form.rfid_tag.data
        precio = form.precio.data
        bodega = form.bodega.data
        uva = form.uva.data
        cosecha = form.cosecha.data
        temperatura = form.temperatura.data
        humedad = form.humedad.data
        latitud = form.latitud.data
        longitud = form.longitud.data

        url = f"{os.environ.get('API_ADDRESS')}/api/assets"
        check_url = f"{os.environ.get('API_ADDRESS')}/api/assets/{rfid_value}"
        headers = {
            "X-api-key": get_api_key(),
        }

       
        body = {
            "Role": "admin",
            "ID": rfid_value,
            "Price": precio,
            "Winery": bodega,
            "Varietal": uva,
            "Year": cosecha,
            "Temperature": temperatura,
            "Humidity": humedad,
            "Latitude": latitud,
            "Longitude": longitud,
            "Owner": "Org1MSP"
        }

        try:
            #chequear aca
            #configuracion
            #api con datos que faltan
            response = requests.options(check_url,headers=headers)
            if(response.status_code == 404):
                response = requests.post(url, json=body, headers=headers)

                if response is None:
                    raise requests.RequestException("No se recibió respuesta.")
                
                wine_info = WINE_VARIETALS.get(uva)
                if wine_info:
                    if not (wine_info["temp_min"] <= temperatura <= wine_info["temp_max"]):
                        flash(f"Advertencia: La temperatura {temperatura}°C no es adecuada para {uva} "
                            f"({wine_info['category']}). Rango recomendado de transporte: "
                            f"{wine_info['temp_min']}-{wine_info['temp_max']}°C.", "warning")

                if not (HUM_MIN <= humedad <= HUM_MAX):
                    flash(f"Advertencia: La humedad {humedad}% está fuera del rango permitido ({HUM_MIN}-{HUM_MAX}).", "warning")

                print(response.json())
                if response.status_code == 200:
                    handle_success(response)
                    time.sleep(0.1)
                    return redirect('/assets')
                elif response.status_code == 202:
                    handle_job_created(response, headers)
                    time.sleep(0.1)
                    return redirect('/assets')
                else:
                    handle_error(response)
            elif (response.status_code == 200):
                flash(f"Error en la solicitud. El asset ya está registrado en la blockchain", 'error')
            else:
                handle_error(response)

        except requests.RequestException as e:
            print(e)
            flash(f"Error en la solicitud: {e}", 'error')

    return render_template('new_asset.html', form=form)

@app.route("/update_asset/<string:asset_id>", methods=['GET', 'POST'])
def update_asset(asset_id):
    form = UpdateAssetForm()
    config = load_wine_config()
    WINE_VARIETALS = config["WINE_VARIETALS"]
    if request.method == 'POST' and form.validate_on_submit():
        url = f"{os.environ.get('API_ADDRESS')}/api/assets/{asset_id}"
        headers = {
            "X-api-key": get_api_key(),
        }
        
        precio = form.precio.data
        bodega = form.bodega.data
        uva = form.uva.data
        cosecha = form.cosecha.data
        temperatura = form.temperatura.data
        humedad = form.humedad.data
        latitud = form.latitud.data
        longitud = form.longitud.data
        owner = form.owner.data

        wine_info = WINE_VARIETALS.get(uva)
        if wine_info:
            if not (wine_info["temp_min"] <= temperatura <= wine_info["temp_max"]):
                flash(f"Advertencia: La temperatura {temperatura}°C no es adecuada para {uva} "
                    f"({wine_info['category']}). Rango recomendado de transporte: "
                    f"{wine_info['temp_min']}-{wine_info['temp_max']}°C.", "warning")

        if not (HUM_MIN <= humedad <= HUM_MAX):
            flash(f"Advertencia: La humedad {humedad}% está fuera del rango permitido ({HUM_MIN}-{HUM_MAX}).", "warning")

      
        body = {
                "Role": "admin",
                "ID": asset_id,
                "Price": precio,
                "Winery": bodega,
                "Varietal": uva,
                "Year": cosecha,
                "Temperature": temperatura,
                "Humidity": humedad,
                "Latitude": latitud,
                "Longitude": longitud,
                "Owner": owner
            }

        try:
            response = requests.put(url, json=body, headers=headers)

            if response is None:
                raise requests.RequestException("No se recibió respuesta.")
            
            if response.status_code == 200:
                handle_success(response)
                return redirect(url_for('assets'))
            elif response.status_code == 202:
                handle_job_created(response, headers)
                return redirect(url_for('assets'))
            else:
                handle_error(response)

        except requests.RequestException as e:
            flash(f"Error en la solicitud: {e}", 'error')

    # Realiza una petición GET para obtener los detalles del activo
    url = f"{os.environ.get('API_ADDRESS')}/api/assets/{asset_id}"
    headers = {
        "X-api-key": get_api_key(),
    }
    
    try:
        response = requests.get(url, headers=headers)

        if not response.ok:
            handle_error(response)
            flash(f"Error al obtener los detalles del activo. Código: {response.status_code}", 'error')
            return redirect(url_for('index'))
        response_json = response.json()
        # Crea una instancia del formulario y llena los campos con los datos del activo
        form.precio.data = response_json['Price']
        form.bodega.data = response_json['Winery']
        form.uva.data = response_json['Varietal']
        form.cosecha.data = response_json['Year']
        form.humedad.data = response_json['Humidity']
        form.temperatura.data = response_json['Temperature']
        form.latitud.data = response_json['Latitude']
        form.longitud.data = response_json['Longitude']
        form.owner.data = response_json['Owner']

        coordenadas = ({'latitude': response_json['Latitude'], 'longitude': response_json['Longitude']})

    except requests.RequestException as e:
        flash(f"Error en la solicitud: {e}", 'error')
        return redirect(url_for('index'))

    return render_template('update_asset.html', form=form, asset_id=asset_id, coordenadas=coordenadas, rol_usuario=current_user.role)

@app.route("/transfer_asset/<string:asset_id>", methods=['GET', 'POST'])
def transfer_asset(asset_id):

    form = TransferAssetForm()
    next_page = request.args.get('next', 'index')  

    if get_org() == "Org1MSP":
        form.owner.choices = [('Org2MSP', 'Transportador')]
    elif get_org() == "Org2MSP":
        form.owner.choices = [('Org1MSP', 'Productor'),('Org3MSP', 'Cliente')]
    elif get_org() == "Org3MSP":
        form.owner.choices = [('Org2MSP', 'Transportador')]


    if request.method == 'POST' and form.validate_on_submit():
        # Actualiza los campos del activo con los valores del formulario
        url = f"{os.environ.get('API_ADDRESS')}/api/assets/{asset_id}"
        headers = {
            "X-api-key": get_api_key(),
        }

        owner = form.owner.data

        body = [{
            "Role": "admin",
            "op": "replace",
            "path": "/Owner",
            "value": owner,
        }]

        try:
            response = requests.patch(url, json=body, headers=headers)

            if response is None:
                raise requests.RequestException("No se recibió respuesta.")
            
            if response.status_code == 200:
                handle_success(response)
                return redirect(url_for(request.args.get('next', 'assets')))
            elif response.status_code == 202:
                handle_job_created(response, headers)
                return redirect(url_for(request.args.get('next', 'assets')))
            else:
                handle_error(response)

        except requests.RequestException as e:
            flash(f"Error en la solicitud: {e}", 'error')

    return render_template('transfer_asset.html', form=form, asset_id=asset_id)

@app.route("/asset_history/<string:asset_id>", methods=['GET', 'POST'])
def asset_history(asset_id):
    url = f"{os.environ.get('API_ADDRESS')}/api/assets/history/{asset_id}"
    headers = {
        "X-api-key": get_api_key(),
    }
    try:
        response = requests.get(url, headers=headers)

        if response is None:
            raise requests.RequestException("No se recibió respuesta.")
        if response.status_code == 200:
            response = response.json()
            flash(f"Respuesta de la API: EXITOSA", 'success')
        # Procesar datos antes de pasarlos a la plantilla
            coordenadas = []
            for entry in response:
                data = entry['data']
                data_dict = json.loads(data)
                if data_dict['Owner']  == "Org1MSP":
                    data_dict['Owner'] = "Productor"
                elif data_dict['Owner'] == "Org2MSP":
                    data_dict['Owner'] = "Transportador"
                elif data_dict['Owner'] == "Org3MSP":
                    data_dict['Owner'] = "Cliente"
                seconds = entry['timestamp']['seconds']
                nanos = entry['timestamp']['nanos']
                timestamp = datetime.fromtimestamp(seconds + nanos / 1e9)

                entry['timestamp'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                entry['data'] = data_dict

                coordenadas.append({'latitude': data_dict['Latitude'], 'longitude': data_dict['Longitude'], 'time': entry['timestamp'], 'owner': data_dict['Owner']})
            coordenadas.reverse
            return render_template("asset_history.html", response=response, coordenadas=coordenadas, asset_id=asset_id)
        else:
            handle_error(response)
            return render_template("asset_history.html", response=response, asset_id=asset_id)

    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")

    return render_template("asset_history.html", response=response, asset_id=asset_id)


@app.route('/assets')
def assets():
    url = f"{os.environ.get('API_ADDRESS')}/api/assets"
    headers = {
        "X-api-key": get_api_key(),
    }

    print("=== LLAMANDO A LA API ===")
    print(f"URL: {url}")
    print(f"API Key usada: {headers['X-api-key']}")
    print(f"Organización actual: {get_org()}")

    try:
        response = requests.get(url, headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response text: {response.text[:500]}")  # Solo los primeros 500 caracteres

        if response is None:
            raise requests.RequestException("No se recibió respuesta.")
        if response.status_code == 200:
            filtered_assets = [asset for asset in response.json() if asset.get('Owner') == get_org()]
            flash(f"Respuesta de la API: EXITOSA", 'success')
            return render_template("assets.html", response=filtered_assets)
        else:
            handle_error(response)
            return render_template("assets.html", response=response)

    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")

    return render_template("assets.html", title='Assets', response=response)

@app.route('/assets_historial')
def assets_historial():
    url = f"{os.environ.get('API_ADDRESS')}/api/assets"
    headers = {
        "X-api-key": get_api_key(),
    }
    response=None
    
    try:
        response = requests.get(url, headers=headers)
        print(response)
        if response is None:
            print("----Response None------------")
            raise requests.RequestException("No se recibió respuesta.")
        if response.status_code == 200:
            flash(f"Respuesta de la API: EXITOSA", 'success')
            response = response.json()
            for asset in response:
                if asset['Owner']  == "Org1MSP":
                    asset['Owner'] = "Productor"
                elif asset['Owner'] == "Org2MSP":
                    asset['Owner'] = "Transportador"
                elif asset['Owner'] == "Org3MSP":
                    asset['Owner'] = "Cliente"
            return render_template("assets_historial.html", response=response)
        else:
            handle_error(response)
            return render_template("assets_historial.html", response=response)

    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")

    return render_template("assets_historial.html", title='Assets historial', response=response)

@app.route('/exportar_mis_assets_csv')
@login_required 
def exportar_mis_assets_csv():
    url = f"{os.environ.get('API_ADDRESS')}/api/assets"
    headers = {
        "X-api-key": get_api_key(),
    }
    org_actual = get_org()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        assets_raw = response.json()
        
        filtered_assets = [asset for asset in assets_raw if asset.get('Owner') == org_actual]

        output = BytesIO()
        si = StringIO()
        cw = csv.writer(si, delimiter=';') 
        
        headers = ['ID', 'Precio', 'Bodega', 'Uva', 'Año', 'Temperatura (°C)', 'Humedad (%)', 'Latitud', 'Longitud', 'Propietario (Org)']
        cw.writerow(headers)
        
        for asset in filtered_assets:
            row = [
                asset.get('ID', 'N/A'),
                f"${asset.get('Price', '0')}", 
                asset.get('Winery', ''),
                asset.get('Varietal', ''),
                asset.get('Year', ''),
                f"{asset.get('Temperature', '')}", 
                f"{asset.get('Humidity', '')}", 
                asset.get('Latitude', ''),
                asset.get('Longitude', ''),
                org_actual 
            ]
            cw.writerow(row)
       
        output.write(u'\ufeff'.encode('utf8'))
        output.write(si.getvalue().encode('utf8'))
        output.seek(0)
        
        return Response(
            output.read(), 
            mimetype="text/csv",
            headers={
              "Content-Disposition": "attachment; filename=mis_assets.csv",
             "Content-type": "text/csv; charset=utf-8" 
        }
    )

    except requests.exceptions.HTTPError as e:
        flash(f"Error HTTP al obtener assets para exportar: {e}", "error")
        return redirect(url_for('assets'))
    except requests.exceptions.RequestException as e:
        flash(f"Error de conexión al obtener assets para exportar: {e}", "error")
        return redirect(url_for('assets'))
    except Exception as e:
        flash(f"Error inesperado al generar CSV: {e}", "error")
        return redirect(url_for('assets'))

@app.route('/exportar_historico_assets_csv')
@login_required 
def exportar_historico_assets_csv():

    url = f"{os.environ.get('API_ADDRESS')}/api/assets"
    headers = {
        "X-api-key": get_api_key(),
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        assets_raw = response.json()

        output = BytesIO()
        si = StringIO()
    
        cw = csv.writer(si, delimiter=';') 

        headers = ['ID', 'Precio', 'Bodega', 'Uva', 'Año', 'Temperatura (°C)', 'Humedad (%)', 'Latitud', 'Longitud', 'Propietario (Org)']
        cw.writerow(headers)


        for asset in assets_raw:
            owner_name = "N/A"
            if asset.get('Owner') == "Org1MSP": owner_name = "Productor"
            elif asset.get('Owner') == "Org2MSP": owner_name = "Transportador"
            elif asset.get('Owner') == "Org3MSP": owner_name = "Cliente"

            row = [
                asset.get('ID', 'N/A'),
                f"${asset.get('Price', '0')}", 
                asset.get('Winery', ''),
                asset.get('Varietal', ''),
                asset.get('Year', ''),
                f"{asset.get('Temperature', '')}",
                f"{asset.get('Humidity', '')}",  
                asset.get('Latitude', ''),
                asset.get('Longitude', ''),
                owner_name 
            ]
            cw.writerow(row)


        output.write(u'\ufeff'.encode('utf8')) 
        output.write(si.getvalue().encode('utf8'))
        output.seek(0)

        return Response(
            output.read(), 
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=todos_assets.csv",
                "Content-type": "text/csv; charset=utf-8" 
        }
    )

    except requests.exceptions.HTTPError as e:
        flash(f"Error HTTP al obtener assets para exportar: {e}", "error")
        return redirect(url_for('assets_historial'))
    except requests.exceptions.RequestException as e:
        flash(f"Error de conexión al obtener assets para exportar: {e}", "error")
        return redirect(url_for('assets_historial'))
    except Exception as e:
        flash(f"Error inesperado al generar CSV: {e}", "error")
        return redirect(url_for('assets_historial'))


@app.route('/exportar_asset_history_csv/<string:asset_id>')
@login_required 
def exportar_asset_history_csv(asset_id):

    url = f"{os.environ.get('API_ADDRESS')}/api/assets/history/{asset_id}"
    headers = {
        "X-api-key": get_api_key(),
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        history_raw = response.json()

        output = BytesIO()
        si = StringIO()
        cw = csv.writer(si, delimiter=';') 

        headers = [
          'TxID', 'Timestamp', 'IsDelete', 'ID', 'Precio', 'Bodega', 'Uva', 'Año', 
           'Temperatura (°C)', 'Humedad (%)', 'Latitud', 'Longitud', 'Propietario (Org)'
        ]
        cw.writerow(headers)

        for entry in history_raw:
            data_dict = json.loads(entry['data'])

            seconds = entry['timestamp']['seconds']
            nanos = entry['timestamp']['nanos']
            timestamp = datetime.fromtimestamp(seconds + nanos / 1e9).strftime('%Y-%m-%d %H:%M:%S.%f')

            owner_name = "N/A"
            if data_dict.get('Owner') == "Org1MSP": owner_name = "Productor"
            elif data_dict.get('Owner') == "Org2MSP": owner_name = "Transportador"
            elif data_dict.get('Owner') == "Org3MSP": owner_name = "Cliente"

            row = [
                entry.get('txId', 'N/A'),
                timestamp,
                entry.get('isDelete', False),
                data_dict.get('ID', 'N/A'),
                data_dict.get('Price', '0'), 
                data_dict.get('Winery', ''),
                data_dict.get('Varietal', ''),
                data_dict.get('Year', ''),
                data_dict.get('Temperature', ''),
                data_dict.get('Humidity', ''),
                data_dict.get('Latitude', ''),
                data_dict.get('Longitude', ''),
                owner_name 
            ]
            cw.writerow(row)

        # Preparación de la respuesta
        output.write(u'\ufeff'.encode('utf8'))
        output.write(si.getvalue().encode('utf8'))
        output.seek(0)

        return Response(
            output.read(), 
            mimetype="text/csv",
            headers={
               "Content-Disposition": f"attachment; filename=historial_activo_{asset_id}.csv",
               "Content-type": "text/csv; charset=utf-8" 
        }
    )

    except requests.exceptions.HTTPError as e:
        flash(f"Error HTTP al obtener el historial para exportar: {e}", "error")
        return redirect(url_for('asset_history', asset_id=asset_id))
    except requests.exceptions.RequestException as e:
        flash(f"Error de conexión al obtener el historial para exportar: {e}", "error")
        return redirect(url_for('asset_history', asset_id=asset_id))
    except Exception as e:
        flash(f"Error inesperado al generar CSV: {e}", "error")
        return redirect(url_for('asset_history', asset_id=asset_id))




@app.route("/config")
@login_required
def config_home():
    config = load_wine_config()

    # Ordenar por categoría y luego por nombre de varietal
    varietals = dict(
        sorted(
            config["WINE_VARIETALS"].items(),
            key=lambda x: (x[1]["category"].lower(), x[0].lower())
        )
    )

    return render_template("config/list.html", varietals=varietals)

@app.route("/config/edit/<string:name>", methods=["GET", "POST"])
@login_required
def config_edit(name):
    config = load_wine_config()
    varietals = config["WINE_VARIETALS"]

    if name not in varietals:
        flash("La variedad no existe.", "error")
        return redirect(url_for("config_home"))

    form = EditVarietalForm()

    if request.method == "POST" and form.validate_on_submit():
        updated_name = form.name.data

        # Si el nombre cambió, se renueva la clave
        if updated_name != name:
            varietals[updated_name] = varietals.pop(name)

        varietals[updated_name]["category"] = form.category.data
        varietals[updated_name]["temp_min"] = form.temp_min.data
        varietals[updated_name]["temp_max"] = form.temp_max.data

        save_wine_config(config)
        flash("Variedad actualizada correctamente.", "success")
        return redirect(url_for("config_home"))

    # Cargar datos al formulario
    form.name.data = name
    form.category.data = varietals[name]["category"]
    form.temp_min.data = varietals[name]["temp_min"]
    form.temp_max.data = varietals[name]["temp_max"]

    return render_template("config/edit.html", form=form)

@app.route("/config/new", methods=["GET", "POST"])
@login_required
def config_new():
    form = NewVarietalForm()

    if request.method == "POST" and form.validate_on_submit():
        config = load_wine_config()
        varietals = config["WINE_VARIETALS"]

        name = form.name.data
        if name in varietals:
            flash("La variedad ya existe.", "error")
            return redirect(url_for("config_home"))

        varietals[name] = {
            "category": form.category.data,
            "temp_min": form.temp_min.data,
            "temp_max": form.temp_max.data
        }

        save_wine_config(config)
        flash("Nueva variedad agregada.", "success")
        return redirect(url_for("config_home"))

    return render_template("config/new.html", form=form)

@app.route("/config/delete/<string:name>", methods=["POST"])
@login_required
def config_delete(name):
    config = load_wine_config()
    varietals = config["WINE_VARIETALS"]

    if name in varietals:
        del varietals[name]
        save_wine_config(config)
        flash("Variedad eliminada.", "success")

    return redirect(url_for("config_home"))
