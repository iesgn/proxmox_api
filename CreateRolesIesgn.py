from pm_gn import *
import sys
pgn=ConectarProxmox()
roles=[{"nombre":"iesgn","privs":"VM.Clone, VM.Allocate, VM.Config.CPU, Pool.Audit, VM.Snapshot, VM.Config.HWType, \
     VM.Config.Network, VM.Config.CDROM, Sys.Audit, VM.Config.Disk, Sys.Syslog, Sys.Console, Datastore.AllocateSpace,\
     VM.Config.Memory, VM.Backup, VM.Config.Options, VM.PowerMgmt, VM.Console, VM.Migrate, Datastore.Audit, Sys.Modify,\
     VM.Config.Cloudinit, Permissions.Modify, VM.Audit, VM.Monitor, Datastore.Allocate","VM.SnapShot.Rollback"},\
    {"nombre":"iesgn-template-clone","privs":"Pool.Audit, VM.Clone, VM.Audit"}
    ]
# Creo los roles del IESGN
for rol in roles:
    try:
        pgn.access.roles.create(roleid=rol["nombre"],privs=rol["privs"])
    except:
        print("Ya está creado el rol:",rol["nombre"])

# Creo el pool imagenes

try:
    pgn.pools.create(poolid="Imagenes")
except:
    print("Pool imágenes ya creado")

# Asigno a los grupos que hay el rol iesgn-template-clone, para el pool imágenes

for grupo in GetGrupos(pgn):
    try:
        pgn.access.acl.set(path="/pool/Imagenes",roles="iesgn-template-clone",groups=grupo)
    except:
        print("Ya está asignado el rol iesgn-template-clone al grupo:",grupo)

# Asigno el rol iesgn al grupo de profesores sobrel pool de imágenes para que puedan crear imágnes en él

try:
    pgn.access.acl.set(path="/pool/Imagenes",roles="iesgn",groups="profesores-iesgn")
except:
    print("Ya está asignado el rol iesgn al grupo profesores.")
