import os
import subprocess
import sys

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def ejecutar_script(nombre_script, argumento=""):
    ruta_script = os.path.join(os.path.dirname(__file__), nombre_script)
    
    if not os.path.exists(ruta_script):
        print(f"\n[!] Error: No se encontró el archivo '{nombre_script}' en este directorio.")
        input("\nPresiona ENTER para volver al menú...")
        return

    print(f"\n" + "="*55)
    etiqueta_modo = f" ({'Modo Oculto' if argumento == '--oculto' else 'Modo Visual'})" if argumento else ""
    print(f"   EJECUTANDO: {nombre_script}{etiqueta_modo}")
    print("="*55 + "\n")
    
    # Ejecuta el script usando el mismo intérprete de Python activo, agregando el argumento si existe
    comando = [sys.executable, ruta_script]
    if argumento:
        comando.append(argumento)
        
    subprocess.run(comando)
    
    print("\n" + "="*55)
    print(f"   FINALIZÓ LA EJECUCIÓN DE: {nombre_script}")
    print("="*55)
    input("\nPresiona ENTER para volver al menú principal...")

def menu_principal():
    while True:
        limpiar_pantalla()
        print("=====================================================")
        print("         CENTRO DE AUTOMATIZACIÓN - PMR              ")
        print("=====================================================")
        print("  [1] GNP Inpart (Visual)")
        print("  [2] GNP Inpart (Oculto)")
        print("  [3] Multiasistencia (Visual)")
        print("  [4] Multiasistencia (Oculto)")
        print("  [5] Cotizaciones Multi")
        print("  [6] Salir")
        print("=====================================================")
        
        opcion = input("Selecciona una opción (1-6): ").strip()
        
        if opcion == "1":
            ejecutar_script("gnp_inpart.py", "--visual")
        elif opcion == "2":
            ejecutar_script("gnp_inpart.py", "--oculto")
        elif opcion == "3":
            ejecutar_script("sincronizador_multiasistencia.py", "--visual")
        elif opcion == "4":
            ejecutar_script("sincronizador_multiasistencia.py", "--oculto")
        elif opcion == "5":
            ejecutar_script("Cotizaciones_Diarias_Multi.py")
        elif opcion == "6":
            print("\nSaliendo del sistema...")
            break
        else:
            input("\nOpción no válida. Presiona ENTER para intentar de nuevo...")

if __name__ == "__main__":
    menu_principal()