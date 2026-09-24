from pm_gn import *
import sys

# Borra las VNets de la zona ZONA (y sus ACLs) de un usuario o de todos los usuarios
# de un grupo. Con --huerfanas borra además las VNets cuyo usuario ya no existe.
# Las VNets a las que está conectada alguna MV/CT no se borran.
#   python3 DeleteRedesProyecto.py <usuario|grupo> [--huerfanas] [--dry-run]
#   python3 DeleteRedesProyecto.py --huerfanas [--dry-run]

argv=[a for a in sys.argv[1:] if not a.startswith("--")]
opciones=[a for a in sys.argv[1:] if a.startswith("--")]
dry_run="--dry-run" in opciones
huerfanas="--huerfanas" in opciones
for opcion in opciones:
    if opcion not in ("--dry-run","--huerfanas"):
        print("Opción desconocida:",opcion)
        sys.exit(1)

pgn=ConectarProxmox()
uso="Uso: python3 DeleteRedesProyecto.py <usuario|grupo> [--huerfanas] [--dry-run]\n     python3 DeleteRedesProyecto.py --huerfanas [--dry-run]"
if len(argv)>1 or (len(argv)==0 and not huerfanas):
    print(uso)
    sys.exit(1)

usuarios_existentes=GetUsuarios(pgn)
usuarios=[]
if argv:
    if argv[0] in usuarios_existentes:
        usuarios=[argv[0]]
    elif EsGrupo(pgn,argv[0]):
        usuarios=GetUsuariosGrupo(pgn,argv[0])
    else:
        print("Usuario/grupo incorrecto.")
        print(uso)
        sys.exit(1)

vnets_zona=[v for v in GetVnets(pgn) if v.get("zone")==ZONA]
a_borrar={}
elegidas=set()
for usuario in usuarios:
    for vnet in vnets_zona:
        if EsRedDe(vnet,usuario):
            a_borrar.setdefault(usuario,[]).append(vnet)
            elegidas.add(vnet["vnet"])
if huerfanas:
    nombres_existentes={NombreUsuario(u) for u in usuarios_existentes}
    for vnet in vnets_zona:
        datos=LeerAlias(vnet.get("alias"))
        if datos is None:
            alert("La VNet %s no tiene un alias reconocible ('%s'), no se toca." % (vnet["vnet"],vnet.get("alias","")))
        elif datos[0] not in nombres_existentes and vnet["vnet"] not in elegidas:
            a_borrar.setdefault(datos[0]+" (no existe)",[]).append(vnet)

total=sum(len(v) for v in a_borrar.values())
if total==0:
    print("No hay VNets que borrar.")
    sys.exit(0)

if not dry_run:
    resp=input("Cuidado!!!. Se borrarán %d VNets de %d usuarios. Si estás seguro pulsa (s)!!!!" % (total,len(a_borrar)))
    if resp!="s":
        sys.exit(0)

en_uso=GetBridgesEnUso(pgn)
acls=GetACL(pgn)
borradas=0
for usuario,vnets in a_borrar.items():
    warning(usuario)
    for vnet in vnets:
        if EliminarRed(pgn,vnet,en_uso,acls,dry_run):
            borradas+=1

if borradas and not dry_run:
    AplicarSDN(pgn)
