from pm_gn import *
import sys

# Deja a un grupo de alumnos solo los bridges compartidos (BRIDGES_COMPARTIDOS) de la
# zona localnetwork: da iesgn-bridge sobre cada bridge compartido y después quita el
# rol iesgn-red sobre toda la zona. Si ya está así, no hace nada.
#   python3 PermisosLocalnetwork.py <grupo> [--dry-run]

argv=[a for a in sys.argv[1:] if a!="--dry-run"]
dry_run="--dry-run" in sys.argv[1:]

pgn=ConectarProxmox()
if len(argv)!=1 or not EsGrupo(pgn,argv[0]):
    print("Uso: python3 PermisosLocalnetwork.py <grupo> [--dry-run]")
    print("Grupos:",GetGrupos(pgn))
    sys.exit(1)
grupo=argv[0]
if grupo=="profesores-iesgn":
    alert("Los profesores mantienen iesgn-red sobre toda la zona localnetwork.")
    sys.exit(1)
if not ExisteRol(pgn,ROL_BRIDGE):
    alert("No existe el rol %s. Ejecuta antes CreateRolesIesgn.py" % ROL_BRIDGE)
    sys.exit(1)

accion="[dry-run]" if dry_run else "[OK]"
acls=GetACL(pgn)
try:
    for bridge in BRIDGES_COMPARTIDOS:
        path="/sdn/zones/localnetwork/"+bridge
        if TieneACL(acls,path,ROL_BRIDGE,grupo):
            print("[YA EXISTE] %s -> %s -> %s" % (grupo,ROL_BRIDGE,path))
        else:
            if not dry_run:
                pgn.access.acl.set(path=path,roles=ROL_BRIDGE,groups=grupo)
            print("%s %s -> %s -> %s" % (accion,grupo,ROL_BRIDGE,path))

    path="/sdn/zones/localnetwork"
    if TieneACL(acls,path,"iesgn-red",grupo):
        if not dry_run:
            pgn.access.acl.set(path=path,roles="iesgn-red",groups=grupo,delete=1)
        print("%s Quitado %s -> iesgn-red -> %s" % (accion,grupo,path))
    else:
        print("[YA ESTÁ] %s no tiene iesgn-red sobre %s" % (grupo,path))
except ResourceException as e:
    alert("Problemas al modificar los permisos de %s: %s" % (grupo,e))
