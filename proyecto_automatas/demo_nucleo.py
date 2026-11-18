"""Recorrido por consola de todo el núcleo: finitos, traductores, pila y Turing.

    python demo_nucleo.py
"""
from automatas.core import pila, traductores, turing
from automatas.core.finitos import a_afd, a_er, complemento, er_a_afd_minimo, minimizar
from automatas.datos import ejemplos, ejemplos_pila, ejemplos_traductores, ejemplos_turing


def titulo(texto):
    print("\n" + "=" * 72 + f"\n{texto}\n" + "=" * 72)


titulo("1. AFND → AFD (construcción de subconjuntos)")
afnd = ejemplos.afnd_termina_en_01()
r = a_afd(afnd, renombrar=True)
print(afnd.descripcion(), "\n")
for fila in r.filas:
    print(f"  {sorted(fila.origen)} --{fila.simbolo}--> mover={sorted(fila.mover)} "
          f"clausura={sorted(fila.destino)}{'  (nuevo)' if fila.nuevo else ''}")
print("\n" + r.afd.tabla())

titulo("2. Minimización (AFD de 8 estados de la clase)")
m = minimizar(ejemplos.afd_minimizacion_8_estados(), quitar_inaccesibles=False)
for it in m.iteraciones:
    print(it.resumen(["0", "1"]), "\n")
print(m.minimo.tabla())

titulo("3. ER → AFND-λ (Thompson) → AFD → AFD mínimo:  (a|b)*abb")
p = er_a_afd_minimo("(a|b)*abb")
for paso in p.thompson.pasos:
    print(" ", paso.descripcion)
print(f"\nAFND-λ: {len(p.thompson.automata.estados)} estados   "
      f"AFD: {len(p.conversion.afd.estados)} estados   mínimo: {len(p.afd_minimo.estados)} estados\n")
print(p.afd_minimo.tabla())

titulo("4. AF → ER (eliminación de estados) y complemento")
a = ejemplos.afnd_termina_en_01()
res = a_er(a)
for paso in res.pasos:
    print(" ", paso.descripcion.replace("\n", "\n    "))
print("\nER:", res.texto)
print("\nComplemento (completo):\n" + complemento(a).tabla())

titulo("5. Traductores: Moore y Mealy detectando 011")
for fabrica in (ejemplos_traductores.moore_secuencia_011, ejemplos_traductores.mealy_secuencia_011):
    mq = fabrica()
    print(mq.descripcion() + "\n" + mq.tabla() + "\n")
    print(traductores.traducir(mq, "1011011").resumen() + "\n")

titulo("6. Autómata de pila: aⁿbⁿ (estado final)")
print(pila.ejecutar(ejemplos_pila.ap_an_bn_estado_final(), "aabb").resumen())
print()
print(pila.ejecutar(ejemplos_pila.ap_palindromos_pares(), "0110").resumen())

titulo("7. Máquinas de Turing")
mt = ejemplos_turing.mt_omega_c_omega_2_cintas()
t = turing.ejecutar(mt, "abcab")
print(mt.descripcion(), "\n")
for paso in t.pasos[:6]:
    c = paso.configuracion
    print(f"  {paso.indice:>2}: {c.estado}  cinta1={''.join(c.cintas[0]) or '·'}@{c.cabezas[0]}  "
          f"cinta2={''.join(c.cintas[1]) or '·'}@{c.cabezas[1]}")
print("  ...")
print(" ", t.motivo)
mp = ejemplos_turing.mt_complemento_a_uno_multipista()
t = turing.ejecutar(mp, "1100")
print(f"\nComplemento a uno (multipista): entrada 1100 → pista 2 = {turing.contenido(mp, t.final, 0, pista=1)}")
