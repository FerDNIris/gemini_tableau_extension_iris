from ._anvil_designer import client_codeTemplate
from anvil import *
import anvil.server
from anvil import tableau
# Los tipos de Tableau como Mark y DataTable son parte del módulo anvil.tableau
from trexjacket.api import get_dashboard
dashboard = get_dashboard()
import time

class client_code(client_codeTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._data = None
    # Initialize loading indicator (assuming it's part of the form design)
    # Ensure you have a component named 'loading_indicator' in your Anvil form.
    if hasattr(self, 'loading_indicator'):
      self.loading_indicator.visible = False
      self.loading_indicator.text = "Procesando..." # Default text
    else:
      print("Warning: loading_indicator component not found in form design. Please add one for better UX.")
    self.summary.visible = False
    print("Extensión inicializada.")
    dashboard.register_event_handler('selection_changed', self.selection_changed_event_handler)

  def selection_changed_event_handler(self, event):
    user_selections = event.worksheet.get_selected_marks()

    # Guardamos la selección si no está vacía
    if user_selections and len(user_selections) > 0:
      self._data = user_selections
    else:
      # Si el usuario anula la selección, limpiamos los datos guardados
      self._data = None

  def handle_success(self, result):
    """Callback for successful server response."""
    if hasattr(self, 'loading_indicator'):
      self.loading_indicator.visible = False
    self.summary.text = result
    self.summary.visible = True
    self._data = None # Clear data after use

  def handle_error(self, error, prompt, data_to_send, attempt):
    """Callback for server error."""
    MAX_RETRIES = 3

    if attempt < MAX_RETRIES:
      # Notificación inicial del error
      Notification(f"Intento {attempt} fallido. Reintentando...", style="warning", timeout=2).show()

      # Cuenta regresiva visual en el loading_indicator
      for i in range(5, 0, -1):
        if hasattr(self, 'loading_indicator'):
          self.loading_indicator.visible = True
          self.loading_indicator.text = f"Error de conexión. Reintentando en {i} segundos..."
        time.sleep(1) # Anvil permite sleep en el cliente sin bloquear el navegador por completo

        # Realizar el siguiente intento
      self.make_analysis_request(prompt, data_to_send, attempt + 1)
    else:
      if hasattr(self, 'loading_indicator'):
        self.loading_indicator.visible = False

      if isinstance(error, anvil.server.TimeoutError):
        self.summary.text = f"La operación falló tras {MAX_RETRIES} intentos por exceso de tiempo. Por favor, intenta con menos datos."
      else:
        self.summary.text = f"Ocurrió un error persistente tras {MAX_RETRIES} intentos:\n{str(error)}"
      self.summary.visible = True
      self._data = None

  def make_analysis_request(self, prompt, data_to_send, attempt=1):
    """Encapsula la llamada al servidor con lógica de reintento."""
    if hasattr(self, 'loading_indicator'):
      self.loading_indicator.text = f"Procesando (Intento {attempt}/3)..."
      self.loading_indicator.visible = True

    server_call_result = anvil.server.call('generateDataSummary', prompt=prompt, data=data_to_send)

    if hasattr(server_call_result, 'then') and callable(server_call_result.then):
      server_call_result.then(
        lambda result: self.handle_success(result)
      ).catch(
        lambda error: self.handle_error(error, prompt, data_to_send, attempt)
      )
    else:
      # Si la respuesta no es una promesa, manejamos el resultado directo
      if isinstance(server_call_result, str) and server_call_result.startswith("Error"):
        self.handle_error(server_call_result, prompt, data_to_send, attempt)
      else:
        self.handle_success(server_call_result)

  def btn_submit_click(self, **event_args):
    """This method is called when the button is clicked"""
    ### Este métido se llama cada vez que el botón de pregunta se da click
    data_to_send = self._data

    # Si el usuario no ha seleccionado datos, obtenemos los datos de TODAS las hojas del dashboard.
    if not data_to_send:
      # Esto proporciona un contexto general del dashboard filtrado.
      Notification("No hay selección. Analizando todas las hojas del dashboard...", timeout=3).show()
      try:
        # El método 'get_summary_data_for_all_worksheets' no existe.
        # La forma correcta es iterar sobre cada hoja de cálculo y recopilar sus datos.
        all_data = {}
        for worksheet in dashboard.worksheets: # Iterate through all worksheets
          # Obtenemos los datos de cada hoja y los guardamos en un diccionario.
          summary_data = worksheet.get_summary_data()
          # print(summary_data) # Debugging line, can be removed
          # Se manejan dos casos: que get_summary_data() devuelva un objeto con atributo .data
          # o que devuelva directamente una lista de datos (ej. lista de diccionarios).
          if (hasattr(summary_data, 'data') and summary_data.data) or (isinstance(summary_data, list) and summary_data):
            all_data[worksheet.name] = summary_data

        data_to_send = all_data
        if not data_to_send:
          Notification("No se encontraron datos en ninguna hoja del dashboard.", style="warning", timeout=5).show()
          return
      except Exception as e:
        Notification(f"Error al obtener datos de las hojas: {e}", style="danger", timeout=5).show()
        return

    # --- Nueva lógica para advertencia de volumen de datos ---
    ### Para no pasarnos de los tokens
    MAX_ROWS_THRESHOLD = 3000 # Define el umbral máximo de filas
    row_count = 0

    if data_to_send:
      # Usamos "duck typing" para contar las filas según el tipo de datos.
      if isinstance(data_to_send, list):
        # Caso 1: Selección de marcas (get_selected_marks).
        row_count = len(data_to_send)
      elif isinstance(data_to_send, dict):
        # Caso 2: Datos de todas las hojas.
        for data_from_sheet in data_to_send.values():
          # Comprueba si es un objeto tipo DataTable
          if hasattr(data_from_sheet, 'data') and isinstance(getattr(data_from_sheet, 'data', None), list):
            row_count += len(data_from_sheet.data)
            # Comprueba si es una lista de datos directamente
          elif isinstance(data_from_sheet, list):
            row_count += len(data_from_sheet)
      elif hasattr(data_to_send, 'data') and isinstance(getattr(data_to_send, 'data', None), list):
        # Caso 3: Datos de una sola hoja (fallback de get_summary_data).
        row_count = len(data_to_send.data)

    if row_count > MAX_ROWS_THRESHOLD:
      warning_message = (
        f"Estás a punto de enviar {row_count} filas de datos. "
        f"Esto puede consumir muchos tokens y afectar el rendimiento o el costo del LLM. "
        f"¿Deseas continuar?"
      )
      # Muestra un cuadro de diálogo de confirmación al usuario
      if not confirm(warning_message, title="Advertencia de Gran Volumen de Datos", buttons=[("Continuar", True), ("Cancelar", False)]):
        Notification("Operación cancelada por el usuario.", timeout=2).show()
        return # Detiene la ejecución si el usuario cancela
    # --- Fin de la nueva lógica ---

    if not self.user_question.text:
      Notification("Por favor, ingresa una pregunta antes de analizar los datos.", style="warning", timeout=3).show()
      return

    self.summary.visible = False # Hide previous summary

    # Iniciar la cadena de peticiones con el primer intento
    self.make_analysis_request(self.user_question.text, data_to_send, attempt=1)

  def btn_clear_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.summary.text = ''
    self.user_question.text = ''
    self._data = None
    self.summary.visible = False
    if hasattr(self, 'loading_indicator'):
      self.loading_indicator.visible = False

