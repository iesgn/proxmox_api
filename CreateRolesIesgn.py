from pm_gn import *
pgn=ConectarProxmox()

# Roles del IESGN (ver infra_iesgn/proxmox/roles.md, Proxmox 9).
# Si el rol ya existe se actualizan sus privilegios a los de esta lista.
roles=[{"nombre":"iesgn","privs":"Datastore.AllocateSpace,Datastore.Audit,Permissions.Modify,Pool.Audit,SDN.Use,\
Sys.Audit,Sys.Console,Sys.Modify,Sys.Syslog,VM.Allocate,VM.Audit,VM.Backup,VM.Clone,VM.Config.CDROM,VM.Config.CPU,\
VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Console,\
VM.Migrate,VM.PowerMgmt,VM.Snapshot,VM.Snapshot.Rollback"},
    {"nombre":"iesgn-red","privs":"SDN.Allocate,SDN.Audit,SDN.Use,Sys.AccessNetwork,Sys.Modify"},
    {"nombre":"iesgn-template-clone","privs":"Pool.Audit,VM.Audit,VM.Clone"},
    {"nombre":"iesgn-template-create","privs":"Pool.Allocate,VM.Allocate"},
    {"nombre":"iesgn-bridge","privs":"SDN.Audit,SDN.Use"}
    ]

# Creo (o actualizo) los roles del IESGN
roles_existentes=[rol["roleid"] for rol in pgn.access.roles.get()]
for rol in roles:
    try:
        if rol["nombre"] in roles_existentes:
            pgn.access.roles(rol["nombre"]).set(privs=rol["privs"])
            print("Rol actualizado:",rol["nombre"])
        else:
            pgn.access.roles.create(roleid=rol["nombre"],privs=rol["privs"])
            print("Rol creado:",rol["nombre"])
    except ResourceException as e:
        alert("Problemas con el rol %s: %s" % (rol["nombre"],e))

# Creo el pool imagenes

if ExisteProyecto(pgn,"Imagenes"):
    print("Pool imágenes ya creado")
else:
    pgn.pools.create(poolid="Imagenes")
    print("Pool imágenes creado")

# A los grupos del IESGN (*-iesgn) les asigno el rol iesgn-template-clone sobre el pool imágenes

for grupo in GetGrupos(pgn):
    if grupo.endswith("-iesgn"):
        pgn.access.acl.set(path="/pool/Imagenes",roles="iesgn-template-clone",groups=grupo)
        print("Asignado iesgn-template-clone sobre /pool/Imagenes al grupo:",grupo)

# Los profesores además pueden crear plantillas en el pool imágenes

pgn.access.acl.set(path="/pool/Imagenes",roles="iesgn-template-create",groups="profesores-iesgn")
print("Asignado iesgn-template-create sobre /pool/Imagenes al grupo: profesores-iesgn")
