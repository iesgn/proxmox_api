from pm_gn import *
import sys

# Crea REDES_POR_USUARIO VNets en la zona ZONA para cada usuario del grupo y le da
# el rol iesgn-bridge sobre ellas. Si ya existen no se tocan, así que se puede
# volver a ejecutar cuando se añaden usuarios al grupo.
#   python3 AddRedesProyecto.py <grupo> [--prefix=xx] [--dry-run]

argv=[a for a in sys.argv[1:] if not a.startswith("--")]
opciones=[a for a in sys.argv[1:] if a.startswith("--")]
dry_run="--dry-run" in opciones
prefijo=None
for opcion in opciones:
    if opcion.startswith("--prefix="):
        prefijo=opcion.split("=",1)[1]
    elif opcion!="--dry-run":
        print("Opción desconocida:",opcion)
        sys.exit(1)

pgn=ConectarProxmox()
if len(argv)!=1 or not EsGrupo(pgn,argv[0]):
    print("Uso: python3 AddRedesProyecto.py <grupo> [--prefix=xx] [--dry-run]")
    print("Grupos:",GetGrupos(pgn))
    sys.exit(1)
grupo=argv[0]

if not ExisteZona(pgn):
    alert("No existe la zona %s. Ejecuta antes CreateZonaProyecto.py" % ZONA)
    sys.exit(1)
if not ExisteRol(pgn,ROL_BRIDGE):
    alert("No existe el rol %s. Ejecuta antes CreateRolesIesgn.py" % ROL_BRIDGE)
    sys.exit(1)

prefijo=prefijo or PrefijoGrupo(grupo)
if not PrefijoValido(prefijo):
    alert("Prefijo '%s' no válido: una letra minúscula y hasta 2 letras/dígitos más." % prefijo)
    sys.exit(1)

vnets=GetVnets(pgn)
acls=GetACL(pgn)
creadas=0
for usuario in GetUsuariosGrupo(pgn,grupo):
    warning(usuario)
    creadas+=CrearRedesUsuario(pgn,usuario,prefijo,vnets,acls,dry_run)

if creadas and not dry_run:
    AplicarSDN(pgn)
elif not creadas:
    print("No se ha creado ninguna VNet, no hace falta aplicar el SDN.")
