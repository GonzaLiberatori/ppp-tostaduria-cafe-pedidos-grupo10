"""Pruebas manuales de los endpoints de actualización puntual de lote."""
import sys
import requests
from decimal import Decimal

# Configuración
BASE_URL = "http://127.0.0.1:8000/api/v1/inventario"
HEADERS = {"Content-Type": "application/json"}

def print_result(test_name, response, expected_status):
    """Imprime el resultado de una prueba."""
    status = "[PASS]" if response.status_code == expected_status else "[FAIL]"
    print(f"\n{status} - {test_name}")
    print(f"  Status: {response.status_code} (esperado: {expected_status})")
    if response.status_code != 200:
        print(f"  Error: {response.json()}")
    return response.status_code == expected_status

def setup_test_data():
    """Crea datos de prueba: tipo de café y lote."""
    print("=" * 60)
    print("PREPARANDO DATOS DE PRUEBA")
    print("=" * 60)
    
    # Crear tipo de café
    tipo_cafe_data = {
        "organico": True,
        "precio_por_kg_verde": "50.00",
        "variedad": "Arábica",
        "region": "Antioquia",
        "pais": "Colombia"
    }
    response = requests.post(f"{BASE_URL}/tipos-de-cafe", json=tipo_cafe_data, headers=HEADERS)
    if response.status_code == 201:
        tipo_cafe_id = response.json()["id"]
        print(f"[OK] Tipo de café creado con ID: {tipo_cafe_id}")
    else:
        print(f"[ERROR] Error creando tipo de café: {response.json()}")
        sys.exit(1)
    
    # Crear lote
    lote_data = {
        "tipo": "VERDE",
        "estado": "ABIERTO",
        "fecha_vencimiento": "2027-12-31T23:59:59",
        "humedad": "12.50",
        "kg_reales": "100.00",
        "ubicacion_fisica": "Depósito A - Estante 1",
        "observaciones": "Lote de prueba",
        "tipo_de_cafe_id": tipo_cafe_id
    }
    response = requests.post(f"{BASE_URL}/lotes", json=lote_data, headers=HEADERS)
    if response.status_code == 201:
        lote_id = response.json()["id"]
        print(f"[OK] Lote creado con ID: {lote_id}")
        print(f"  kg_reales: {response.json()['kg_reales']}")
        print(f"  kg_disponibles: {response.json()['kg_disponibles']}")
        print(f"  estado: {response.json()['estado']}")
        return lote_id
    else:
        print(f"[ERROR] Error creando lote: {response.json()}")
        sys.exit(1)

def test_kg_reales(lote_id):
    """Prueba el endpoint PATCH /lotes/{lote_id}/kg-reales."""
    print("\n" + "=" * 60)
    print("PRUEBAS: PATCH /lotes/{lote_id}/kg-reales")
    print("=" * 60)
    
    results = []
    
    # Test 1: Aumento de kg_reales (debe propagar a kg_disponibles)
    print("\nTest 1: Aumentar kg_reales de 100.00 a 150.00")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/kg-reales",
        json={"kg_reales": "150.00"},
        headers=HEADERS
    )
    results.append(print_result("Aumentar kg_reales", response, 200))
    if response.status_code == 200:
        data = response.json()
        print(f"  kg_reales: {data['kg_reales']} (esperado: 150.00)")
        print(f"  kg_disponibles: {data['kg_disponibles']} (esperado: 150.00)")
        assert data['kg_reales'] == "150.00", "kg_reales no se actualizó correctamente"
        assert data['kg_disponibles'] == "150.00", "kg_disponibles no se propagó correctamente"
    
    # Test 2: Disminución de kg_reales (NO debe afectar kg_disponibles)
    print("\nTest 2: Disminuir kg_reales de 150.00 a 120.00")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/kg-reales",
        json={"kg_reales": "120.00"},
        headers=HEADERS
    )
    results.append(print_result("Disminuir kg_reales", response, 200))
    if response.status_code == 200:
        data = response.json()
        print(f"  kg_reales: {data['kg_reales']} (esperado: 120.00)")
        print(f"  kg_disponibles: {data['kg_disponibles']} (esperado: 150.00 - sin cambios)")
        assert data['kg_reales'] == "120.00", "kg_reales no se actualizó correctamente"
        assert data['kg_disponibles'] == "150.00", "kg_disponibles no debió cambiar"
    
    # Test 3: Lote inexistente
    print("\nTest 3: Actualizar lote inexistente (99999)")
    response = requests.patch(
        f"{BASE_URL}/lotes/99999/kg-reales",
        json={"kg_reales": "200.00"},
        headers=HEADERS
    )
    results.append(print_result("Lote inexistente", response, 404))
    
    return all(results)

def test_kg_disponibles(lote_id):
    """Prueba el endpoint PATCH /lotes/{lote_id}/kg-disponibles."""
    print("\n" + "=" * 60)
    print("PRUEBAS: PATCH /lotes/{lote_id}/kg-disponibles")
    print("=" * 60)
    
    results = []
    
    # Test 1: Actualización válida (menor a kg_reales)
    print("\nTest 1: Actualizar kg_disponibles a 100.00 (actual kg_reales: 120.00)")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/kg-disponibles",
        json={"kg_disponibles": "100.00"},
        headers=HEADERS
    )
    results.append(print_result("Actualización válida", response, 200))
    if response.status_code == 200:
        data = response.json()
        print(f"  kg_disponibles: {data['kg_disponibles']} (esperado: 100.00)")
        print(f"  kg_reales: {data['kg_reales']} (esperado: 120.00 - sin cambios)")
        assert data['kg_disponibles'] == "100.00", "kg_disponibles no se actualizó correctamente"
        assert data['kg_reales'] == "120.00", "kg_reales no debió cambiar"
    
    # Test 2: kg_disponibles excede kg_reales
    print("\nTest 2: kg_disponibles (200.00) > kg_reales (120.00)")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/kg-disponibles",
        json={"kg_disponibles": "200.00"},
        headers=HEADERS
    )
    results.append(print_result("kg_disponibles excede kg_reales", response, 400))
    
    # Test 3: Lote inexistente
    print("\nTest 3: Actualizar lote inexistente (99999)")
    response = requests.patch(
        f"{BASE_URL}/lotes/99999/kg-disponibles",
        json={"kg_disponibles": "50.00"},
        headers=HEADERS
    )
    results.append(print_result("Lote inexistente", response, 404))
    
    return all(results)

def test_estado(lote_id):
    """Prueba el endpoint PATCH /lotes/{lote_id}/estado."""
    print("\n" + "=" * 60)
    print("PRUEBAS: PATCH /lotes/{lote_id}/estado")
    print("=" * 60)
    
    results = []
    
    # Test 1: Cambiar estado a CERRADO
    print("\nTest 1: Cambiar estado de ABIERTO a CERRADO")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/estado",
        json={"estado": "CERRADO"},
        headers=HEADERS
    )
    results.append(print_result("Cambiar a CERRADO", response, 200))
    if response.status_code == 200:
        data = response.json()
        print(f"  estado: {data['estado']} (esperado: CERRADO)")
        assert data['estado'] == "CERRADO", "estado no se actualizó correctamente"
    
    # Test 2: Cambiar estado a ABIERTO
    print("\nTest 2: Cambiar estado de CERRADO a ABIERTO")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/estado",
        json={"estado": "ABIERTO"},
        headers=HEADERS
    )
    results.append(print_result("Cambiar a ABIERTO", response, 200))
    if response.status_code == 200:
        data = response.json()
        print(f"  estado: {data['estado']} (esperado: ABIERTO)")
        assert data['estado'] == "ABIERTO", "estado no se actualizó correctamente"
    
    # Test 3: Estado inválido
    print("\nTest 3: Estado inválido (INVALIDO)")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/estado",
        json={"estado": "INVALIDO"},
        headers=HEADERS
    )
    results.append(print_result("Estado inválido", response, 422))
    
    # Test 4: Lote inexistente
    print("\nTest 4: Actualizar lote inexistente (99999)")
    response = requests.patch(
        f"{BASE_URL}/lotes/99999/estado",
        json={"estado": "CERRADO"},
        headers=HEADERS
    )
    results.append(print_result("Lote inexistente", response, 404))
    
    return all(results)

def test_transacciones(lote_id):
    """Prueba que las transacciones funcionen correctamente."""
    print("\n" + "=" * 60)
    print("PRUEBAS: TRANSACCIONES")
    print("=" * 60)
    
    results = []
    
    # Test 1: Transacción exitosa
    print("\nTest 1: Transacción exitosa (commit)")
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/kg-reales",
        json={"kg_reales": "130.00"},
        headers=HEADERS
    )
    if response.status_code == 200:
        print(f"  [OK] Cambio aplicado correctamente")
        results.append(True)
    else:
        print(f"  [ERROR] Error: {response.json()}")
        results.append(False)
    
    # Verificar persistencia
    response = requests.get(f"{BASE_URL}/lotes/{lote_id}", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(f"  kg_reales persistido: {data['kg_reales']} (esperado: 130.00)")
        assert data['kg_reales'] == "130.00", "Los cambios no se persistieron"
        results.append(True)
    
    # Test 2: Transacción fallida (rollback)
    print("\nTest 2: Transacción fallida (rollback)")
    # Intentar actualizar kg_disponibles a un valor mayor a kg_reales
    response = requests.patch(
        f"{BASE_URL}/lotes/{lote_id}/kg-disponibles",
        json={"kg_disponibles": "999.00"},
        headers=HEADERS
    )
    if response.status_code == 400:
        print(f"  [OK] Transacción rechazada correctamente")
        results.append(True)
    else:
        print(f"  [ERROR] Error: transacción debió fallar pero retornó {response.status_code}")
        results.append(False)
    
    # Verificar que no hubo cambios
    response = requests.get(f"{BASE_URL}/lotes/{lote_id}", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(f"  kg_disponibles sin cambios: {data['kg_disponibles']} (esperado: 110.00)")
        assert data['kg_disponibles'] == "110.00", "Los cambios no debieron persistir"
        results.append(True)
    
    return all(results)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PRUEBAS MANUALES DE ENDPOINTS DE ACTUALIZACIÓN PUNTUAL")
    print("=" * 60)
    
    try:
        lote_id = setup_test_data()
        
        test1 = test_kg_reales(lote_id)
        test2 = test_kg_disponibles(lote_id)
        test3 = test_estado(lote_id)
        test4 = test_transacciones(lote_id)
        
        print("\n" + "=" * 60)
        print("RESUMEN DE PRUEBAS")
        print("=" * 60)
        print(f"[OK] Test kg-reales: {'PASS' if test1 else 'FAIL'}")
        print(f"[OK] Test kg-disponibles: {'PASS' if test2 else 'FAIL'}")
        print(f"[OK] Test estado: {'PASS' if test3 else 'FAIL'}")
        print(f"[OK] Test transacciones: {'PASS' if test4 else 'FAIL'}")
        
        all_pass = all([test1, test2, test3, test4])
        print("\n" + "=" * 60)
        if all_pass:
            print("[OK] TODAS LAS PRUEBAS PASARON")
        else:
            print("[ERROR] ALGUNAS PRUEBAS FALLARON")
        print("=" * 60)
        
        sys.exit(0 if all_pass else 1)
    except Exception as e:
        print(f"\n[ERROR] Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
