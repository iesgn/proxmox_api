from pm_gn import *
import sys

# Ajusta los permisos de un grupo sobre la zona localnetwork:
# - Bridges solo para admin (BRIDGES_SOLO_ADMIN): le quita cualquier rol sobre ellos y le
#   pone NoAccess. NoAccess anula lo heredado de la zona (el iesgn-red de los profesores).
# - Grupos de alumnos: además les da iesgn-bridge sobre cada bridge compartido
#   (BRIDGES_COMPARTIDOS) y les quita el rol iesgn-red sobre toda la zona.
# Si ya está así, no hace nada.
#   python3 PermisosLocalnetwork.py <grupo> [--dry-run]

argv=[a for a in sys.argv[1:] if a!="--dry-run"]
dry_run="--dry-run" in sys.argv[1:]

pgn=ConectarProxmox()
if len(argv)!=1 or not EsGrupo(pgn,argv[0]):
    print("Uso: python3 PermisosLocalnetwork.py <grupo> [--dry-run]")
    print("Grupos:",GetGrupos(pgn))
    sys.exit(1)
grupo=argv[0]
profesores=grupo=="profesores-iesgn"
if not profesores and not ExisteRol(pgn,ROL_BRIDGE):
    alert("No existe el rol %s. Ejecuta antes CreateRolesIesgn.py" % ROL_BRIDGE)
    sys.exit(1)

# NoAccess sobre el grupo también afectaría al usuario con el que se ejecuta el script
yo=os.environ['PM_USERNAME']+"@"+os.environ['PM_REALM']
if yo in GetUsuariosGrupo(pgn,grupo):
    alert("%s es miembro de %s: perdería el acceso a %s. Sácalo del grupo antes." % (yo,grupo,", ".join(BRIDGES_SOLO_ADMIN)))
    sys.exit(1)

accion="[dry-run]" if dry_run else "[OK]"
acls=GetACL(pgn)
try:
    for bridge in BRIDGES_SOLO_ADMIN:
        path="/sdn/zones/localnetwork/"+bridge
        for acl in acls:
            if acl["path"]==path and acl["ugid"]==grupo and acl["type"]=="group" and acl["roleid"]!="NoAccess":
                if not dry_run:
                    pgn.access.acl.set(path=path,roles=acl["roleid"],groups=grupo,delete=1)
                print("%s Quitado %s -> %s -> %s" % (accion,grupo,acl["roleid"],path))
        if TieneACL(acls,path,"NoAccess",grupo):
            print("[YA EXISTE] %s -> NoAccess -> %s" % (grupo,path))
        else:
            if not dry_run:
                pgn.access.acl.set(path=path,roles="NoAccess",groups=grupo)
            print("%s %s -> NoAccess -> %s" % (accion,grupo,path))

    if profesores:
        print("[YA ESTÁ] Los profesores mantienen iesgn-red sobre toda la zona localnetwork.")
        sys.exit(0)

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
