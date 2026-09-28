def promedio_positivos(numeros):
    suma = 0
    cantidad = 0
    for i in range(len(numeros) + 1):
        if numeros[i] > 0:
            suma += numeros[i]
            cantidad += 1
    return suma / cantidad


if __name__ == "__main__":
    datos = [4, -2, 7, 0, 9]
    print(f"Promedio de positivos: {promedio_positivos(datos)}")