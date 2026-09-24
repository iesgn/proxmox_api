from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException
import os
import re
import sys
import time


class color:
   PURPLE = '\033[1;35;48m'
   CYAN = '\033[1;36;48m'
   BOLD = '\033[1;37;48m'
   BLUE = '\033[1;34;48m'
   GREEN = '\033[1;32;48m'
   YELLOW = '\033[1;33;48m'
   RED = '\033[1;31;48m'
   BLACK = '\033[1;30;48m'
   UNDERLINE = '\033[4;37;48m'
   END = '\033[1;37;0m'

def alert(text):
    print(color.RED + text + color.END)

def warning(text):
    print(color.BLUE + text + color.END)

# Storages que se asignan a cada proyecto. Los que no existan en el Proxmox se ignoran.
STORAGE=["local","local-lvm","remoto-lvm"]
def ConectarProxmox():
    try:
        # Por defecto se entra por el proxy inverso (puerto 443, certificado válido).
        # Para ir directo a un nodo (8006, certificado autofirmado): PM_PORT=8006 y PM_VERIFY_SSL=no
        proxmox = ProxmoxAPI(os.environ['PM_SERVER'], port=int(os.environ.get('PM_PORT','443')),
                             user=os.environ['PM_USERNAME']+"@"+os.environ['PM_REALM'],password=os.environ['PM_PASSWORD'],
                             verify_ssl=os.environ.get('PM_VERIFY_SSL','si')!="no")
        proxmox.version.get()
    except KeyError as e:
        print("Falta la variable de entorno %s (¿has hecho source openrc?)." % e)
        sys.exit(1)
    except Exception as e:
        print("Problemas a conectar con el servidor Proxmox Gonzalo Nazareno:", e)
        sys.exit(1)
    return proxmox

def GetUsuarios(pm):
    return [user["userid"] for user in pm.access.users.get()]

def EsUsuario(pm,id):
    return id in GetUsuarios(pm)

def GetGrupos(pm):
    return [group["groupid"] for group in pm.access.groups.get()]

def EsGrupo(pm,idg):
    return idg in GetGrupos(pm)

def GetUsuariosGrupo(pm,idg):
    return pm.access.groups(idg).get().get("members",[])

def EsUsuarioGrupo(pm,id,idg):
    return id in GetUsuariosGrupo(pm,idg)

def NombreProyecto(id):
    return "Proyecto_"+id.replace("@","_")

def ExisteProyecto(pm,newid):
    return newid in [pool["poolid"] for pool in pm.pools.get()]

def GetStorages(pm):
    return [stor["storage"] for stor in pm.storage.get()]

def GetStorageProyecto(pm,newid):
    return [miembro["storage"] for miembro in pm.pools(newid).get()["members"] if miembro["type"]=="storage"]

def AsignarStorageProyecto(pm,newid):
    existentes=GetStorages(pm)
    actuales=GetStorageProyecto(pm,newid)
    for stor in STORAGE:
        if stor in existentes and stor not in actuales:
            pm.pools(newid).set(storage=stor)
            print("Añadiendo storage:",stor)

def CrearProyecto(pm,id):
    newid=NombreProyecto(id)
    try:
        if ExisteProyecto(pm,newid):
            print(newid,"ya existe...")
        else:
            pm.pools.create(poolid=newid)
            print(newid,"creado...")
        AsignarStorageProyecto(pm,newid)
        pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id)
    except ResourceException as e:
        alert("Problemas al crear el proyecto %s: %s" % (newid,e))

def UpdateProyectoStorage(pm,id):
    newid=NombreProyecto(id)
    try:
        AsignarStorageProyecto(pm,newid)
        print(newid,"modificado...")
    except ResourceException as e:
        alert("Problemas al modificar el proyecto %s: %s" % (newid,e))

def GetVMProyecto(pm,id):
    newid=NombreProyecto(id)
    try:
        return [miembro["id"] for miembro in pm.pools(newid).get()["members"] if miembro["type"] in ("qemu","lxc")]
    except ResourceException:
        return []

# Devuelve la entrada de cluster/resources de una MV/CT (node, type, name, status...)
def GetRecursoMV(pm,vmid):
    for recurso in pm.cluster.resources.get(type="vm"):
        if recurso["vmid"]==int(vmid):
            return recurso
    return None

def GetMV(pm,recurso):
    return pm.nodes(recurso["node"])(recurso["type"])(recurso["vmid"])

def EsperarTarea(pm,node,upid):
    while True:
        estado=pm.nodes(node).tasks(upid).status.get()
        if estado["status"]=="stopped":
            return estado.get("exitstatus")=="OK"
        time.sleep(2)

def InfoVM(pm,mv):
    info=GetRecursoMV(pm,mv.split("/")[1])
    text=mv
    espacios=" "*(20-len(info.get("name","")))
    text+="\t"+info.get("name","")+espacios+str(info["maxcpu"])+" - "+str(int(info["maxmem"]/1024/1024))+" - "+str(int(info["maxdisk"]/1024/1024/1024))+"\t"+info["status"]
    return text

# Para (si hace falta) y elimina una MV o CT. Al eliminarla, Proxmox la quita también del pool.
def EliminarMV(pm,mv):
    recurso=GetRecursoMV(pm,mv.split("/")[1])
    if recurso is None:
        alert("No se encuentra la máquina %s." % mv)
        return False
    maquina=GetMV(pm,recurso)
    try:
        if maquina.status.current.get()["status"]!="stopped":
            maquina.status.stop.create()
            while maquina.status.current.get()["status"]!="stopped":
                time.sleep(2)
                print("Parando...",mv)
        if not EsperarTarea(pm,recurso["node"],maquina.delete(purge=1)):
            alert("Error al eliminar la máquina %s (ver el log de tareas de Proxmox)." % mv)
            return False
        print("Eliminando mv:",mv)
        return True
    except ResourceException as e:
        alert("Error al eliminar la máquina %s: %s" % (mv,e))
        return False

def EliminarProyectoMV(pm,id):
    todas=True
    for mv in GetVMProyecto(pm,id):
        if not EliminarMV(pm,mv):
            todas=False
    return todas

def EliminarProyecto(pm,id):
    newid=NombreProyecto(id)
    if not ExisteProyecto(pm,newid):
        print(newid,"no existe...")
        return
    if not EliminarProyectoMV(pm,id):
        alert("No se elimina el proyecto %s porque quedan máquinas." % newid)
        return
    try:
        for stor in GetStorageProyecto(pm,newid):
            pm.pools(newid).set(storage=stor,delete=1)
            print("Eliminando storage:",stor)
        pm.pools(newid).delete()
        print(newid,"eliminado...")
    except ResourceException as e:
        alert("Problemas al eliminar el proyecto %s: %s" % (newid,e))


def ActivarUsuario(pm,id,op):
    try:
        pm.access.users(id).set(enable=op)
        print("Cambiado con éxito el usuario:", id)
    except ResourceException as e:
        alert("Problemas al procesar el usuario %s: %s" % (id,e))


def PermisoUsuarioProyecto(pm,id,proy,op):
    newid=NombreProyecto(proy)
    try:
        if op==1:
            pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id)
            print("Concediendo permisos de %s a %s" % (newid,id))
        if op==0:
            pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id,delete=1)
            print("Quitando permisos de %s a %s" % (newid,id))
    except ResourceException as e:
        alert("Problemas al gestionar %s - %s: %s" % (newid,id,e))


def NewIdMV(pm):
    return int(pm.cluster.nextid.get())


# Clona una plantilla (MV o CT) en el proyecto del usuario. Espera a que termine
# el clonado para que el siguiente NewIdMV no devuelva el mismo id.
def ClonarMV(pm,id,name,user):
    pool=NombreProyecto(user)
    recurso=GetRecursoMV(pm,id)
    if recurso is None:
        alert("No existe la plantilla %s." % id)
        return
    try:
        newid=NewIdMV(pm)
        if recurso["type"]=="qemu":
            upid=GetMV(pm,recurso).clone.create(newid=newid,name=name,pool=pool)
        else:
            upid=GetMV(pm,recurso).clone.create(newid=newid,hostname=name,pool=pool)
        if EsperarTarea(pm,recurso["node"],upid):
            print("Clonada %s en %s (id %d)" % (id,pool,newid))
        else:
            alert("Error al clonar %s en %s (ver el log de tareas de Proxmox)." % (id,pool))
    except ResourceException as e:
        alert("Problemas al clonar MV %s: %s" % (id,e))


# --- Redes SDN por usuario -------------------------------------------------
# Cada usuario tiene REDES_POR_USUARIO VNets en la zona ZONA (switches aislados, sin
# subred), llamadas <prefijo><nnn>n<1..3>. El alias "<usuario> <realm> red<N>" indica
# de quién es cada VNet y permite reconocerlas al volver a ejecutar los scripts.

ZONA="proyecto"
REDES_POR_USUARIO=3
ROL_BRIDGE="iesgn-bridge"
BRIDGES_COMPARTIDOS=["vmbr0","vmbr1"]

def GetACL(pm):
    return pm.access.acl.get()

def TieneACL(acls,path,rol,ugid):
    return any(acl["path"]==path and acl["roleid"]==rol and acl["ugid"]==ugid for acl in acls)

def ExisteRol(pm,rol):
    return rol in [r["roleid"] for r in pm.access.roles.get()]

def ExisteZona(pm,zona=ZONA):
    return zona in [z["zone"] for z in pm.cluster.sdn.zones.get()]

def GetVnets(pm):
    return pm.cluster.sdn.vnets.get()

def AliasRed(id,n):
    return "%s red%d" % (id.replace("@"," "),n)

def EsRedDe(vnet,id):
    return vnet.get("zone")==ZONA and vnet.get("alias","").startswith(id.replace("@"," ")+" red")

# asir2-iesgn -> a2, smr2-iesgn -> s2, profesores-iesgn -> p
def PrefijoGrupo(grupo):
    nombre=grupo.split("-")[0].lower()
    return nombre[0]+"".join(c for c in nombre if c.isdigit())

def PrefijoValido(prefijo):
    # El id de una VNet tiene como máximo 8 caracteres: prefijo + nnn + n + N
    return re.fullmatch(r"[a-z][a-z0-9]{0,2}",prefijo) is not None

def AplicarSDN(pm):
    upid=pm.cluster.sdn.set()
    if EsperarTarea(pm,upid.split(":")[1],upid):
        print("Configuración SDN aplicada.")
    else:
        alert("Error al aplicar la configuración SDN (ver el log de tareas de Proxmox).")

# Crea las VNets que le falten al usuario y le da el rol ROL_BRIDGE sobre cada una.
# vnets y acls son las listas actuales; se actualizan con lo que se crea.
# Devuelve el número de VNets creadas (para saber si hay que aplicar el SDN).
def CrearRedesUsuario(pm,id,prefijo,vnets,acls,dry_run=False):
    propias=[v["vnet"] for v in vnets if EsRedDe(v,id)]
    if propias:
        base=propias[0][:-2]
    else:
        usados={int(v["vnet"][len(prefijo):len(prefijo)+3]) for v in vnets if re.fullmatch(prefijo+r"\d{3}n\d",v["vnet"])}
        libres=[n for n in range(1,1000) if n not in usados]
        if not libres:
            alert("No quedan números libres para el prefijo %s." % prefijo)
            return 0
        base="%s%03d" % (prefijo,libres[0])
    creadas=0
    for n in range(1,REDES_POR_USUARIO+1):
        vnet="%sn%d" % (base,n)
        alias=AliasRed(id,n)
        existente=[v for v in vnets if v["vnet"]==vnet]
        try:
            if existente and existente[0].get("alias")!=alias:
                alert("  La VNet %s ya existe con alias '%s', no se toca." % (vnet,existente[0].get("alias","")))
                continue
            if existente:
                print("  [YA EXISTE] VNet",vnet)
            else:
                if not dry_run:
                    pm.cluster.sdn.vnets.create(vnet=vnet,zone=ZONA,alias=alias)
                vnets.append({"vnet":vnet,"zone":ZONA,"alias":alias})
                creadas+=1
                print("  %s VNet %s (%s)" % ("[dry-run] Crearía" if dry_run else "[OK] Creada",vnet,alias))
            path="/sdn/zones/%s/%s" % (ZONA,vnet)
            if TieneACL(acls,path,ROL_BRIDGE,id):
                print("  [YA EXISTE] ACL",path)
            else:
                if not dry_run:
                    pm.access.acl.set(path=path,roles=ROL_BRIDGE,users=id)
                acls.append({"path":path,"roleid":ROL_BRIDGE,"ugid":id,"type":"user"})
                print("  %s ACL %s -> %s -> %s" % ("[dry-run] Asignaría" if dry_run else "[OK]",path,ROL_BRIDGE,id))
        except ResourceException as e:
            alert("  Problemas con la VNet %s: %s" % (vnet,e))
    return creadas

# "ana iesgn red1" -> "ana@iesgn" (None si el alias no tiene ese formato)
def PropietarioRed(alias):
    nombre=alias.rsplit(" red",1)[0] if " red" in alias else ""
    usuario,_,realm=nombre.rpartition(" ")
    return usuario+"@"+realm if usuario and realm else None

# Bridges/VNets a los que está conectada alguna tarjeta de red de una MV o CT
def GetBridgesEnUso(pm):
    en_uso={}
    for recurso in pm.cluster.resources.get(type="vm"):
        config=GetMV(pm,recurso).config.get()
        for clave,valor in config.items():
            if re.fullmatch(r"net\d+",clave):
                bridge=re.search(r"bridge=([^,]+)",str(valor))
                if bridge:
                    en_uso.setdefault(bridge.group(1),[]).append("%s/%s" % (recurso["type"],recurso["vmid"]))
    return en_uso

# Borra una VNet (si ninguna máquina la usa) y las ACLs sobre ella.
# Devuelve True si se ha borrado (para saber si hay que aplicar el SDN).
def EliminarRed(pm,vnet,en_uso,acls,dry_run=False):
    if vnet["vnet"] in en_uso:
        alert("  VNet %s en uso por %s, no se borra." % (vnet["vnet"]," ".join(en_uso[vnet["vnet"]])))
        return False
    path="/sdn/zones/%s/%s" % (ZONA,vnet["vnet"])
    accion="[dry-run]" if dry_run else "[OK]"
    try:
        if not dry_run:
            pm.cluster.sdn.vnets(vnet["vnet"]).delete()
        print("  %s Borrada VNet %s (%s)" % (accion,vnet["vnet"],vnet.get("alias","")))
        for acl in [a for a in acls if a["path"]==path]:
            if not dry_run:
                if acl["type"]=="group":
                    pm.access.acl.set(path=path,roles=acl["roleid"],groups=acl["ugid"],delete=1)
                else:
                    pm.access.acl.set(path=path,roles=acl["roleid"],users=acl["ugid"],delete=1)
            print("  %s Quitada ACL %s -> %s -> %s" % (accion,path,acl["roleid"],acl["ugid"]))
        return True
    except ResourceException as e:
        alert("  Problemas al borrar la VNet %s: %s" % (vnet["vnet"],e))
        return False
