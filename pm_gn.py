from proxmoxer import ProxmoxAPI
import os
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

STORAGE=["local","local-lvm","remote-lvm"]
def ConectarProxmox():
    try:
        proxmox = ProxmoxAPI(os.environ['PM_SERVER'], user=os.environ['PM_USERNAME']+"@"+os.environ['PM_REALM'],password=os.environ['PM_PASSWORD'], verify_ssl=False)
    except:
        print("Problemas a conectar con el servidor Proxmox Gonzalo Nazareno.")
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
    return  [group["users"] for group in pm.access.groups.get() if group["groupid"]==idg][0].split(",")

def EsUsuarioGrupo(pm,id,idg):
    return id in GetUsuariosGrupo(pm,idg)

def CrearProyecto(pm,id):
    try:
        newid="Proyecto_"+id.replace("@","_")
        pm.pools.create(poolid=newid)
        for stor in STORAGE:
            pm.pools(newid).set(storage=stor)
        pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id)
        print(newid,"creado...")
    except:
        print(id,"ya procesado...")

def GetVMProyecto(pm,id):
    newid="Proyecto_"+id.replace("@","_")
    try:
        return [miembro["id"] for miembro in pm.pools(newid).get()["members"] if not miembro["id"].startswith("storage")]
    except:
        return []

def InfoVM(pm,mv):
    info = pm.nodes("proxmox1").qemu(mv.split("/")[1]).status.current.get()
    text=mv
    espacios=" "*(20-len(info["name"]))
    text+="\t"+info["name"]+espacios+str(info["cpus"])+" - "+str(int(info["maxmem"]/1024/1024))+" - "+str(int(info["maxdisk"]/1024/1024/1024))+"\t"+info["status"]
    return text

def EliminarProyecto(pm,id):
    try:
        newid="Proyecto_"+id.replace("@","_")
        try:
            for stor in STORAGE:
                pm.pools(newid).set(storage=stor,delete=1)
                print("Eliminando storage:",stor)
        except:
            pass
        try:
            for mv in GetVMProyecto(pm,id):
                pm.pools(newid).set(vms=mv.split("/")[1],delete=1)
                print("Quitando mv del proyecto:",mv)
                #try:
                if(pm.nodes("proxmox1").qemu(mv.split("/")[1]).status.current.get()["qmpstatus"]!="stopped"):
                    pm.nodes("proxmox1").qemu(mv.split("/")[1]).status.stop.create()
                while(pm.nodes("proxmox1").qemu(mv.split("/")[1]).status.current.get()["qmpstatus"]!="stopped"):
                    time.sleep(2)
                    print("Parando...",mv)
                pm.nodes("proxmox1").qemu(mv.split("/")[1]).delete(purge=1,skiplock=1)
                print("Eliminando mv:",mv)
                #except:
                #    print("Error al eliminar la máquina...")
        except:
            pass
            
        pm.pools(newid).delete()
        print(newid,"eliminado...")
    except:
        print("Problemas al eliminar el proyecto, quizás no exista...")



def ActivarUsuario(pm,id,op):
    try:
        pm.access.users(id).set(enable=op)
        print("Cambiado con éxito el usuario:", id)
    except:
        print("Problemas al procesar el usuario:",id)


def PermisoUsuarioProyecto(pm,id,proy,op):
    try:
        newid="Proyecto_"+proy.replace("@","_")
        if op==1:
            pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id)
            print("Concediendo permisos de %s a %s" % (newid,id))
        if op==0:
            pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id,delete=1)
            print("Quitando permisos de %s a %s" % (newid,id))
    except:
       print("Problemas al gestionar %s - %s" % (newid,id))


def NewIdMV(pm):
    lista_id=[d['vmid'] for d in pm.cluster.resources.get(type="vm")]
    for id in range(100,10000):
        if id not in lista_id:
            return(id)

def GetId(pm,name,id):
    for mv in GetVMProyecto(pm,id):
        info = pm.nodes("proxmox1").qemu(mv.split("/")[1]).status.current.get()["name"]
        if info==name:
            return mv.split("/")[1]


def ClonarMV (pm,id,name,user):
    pool="Proyecto_"+user.replace("@","_")
    try:
        pm.nodes("proxmox1").qemu(id).clone.create(newid=NewIdMV(pm),node="proxmox1",vmid=int(id),name=name,pool=pool)
    except:
        print("Problemas al clonar MV", id)

def EliminarMV(pm,name,user):
    id=GetId(pm,name,user)
    try:
        pm.nodes("proxmox1").qemu(GetId(pm,name,user)).delete()
    except:
        print("Problemas al eliminar MV", GetId(pm,name,user))



def TestDiscosHuerfanos(pm):
    STOR=["local-lvm","remote-lvm"]
    for store in STOR:
        print(store)
        discos=[d["volid"] for d in pm.nodes("proxmox1").storage(store).content.get()]
        for vm in [d['vmid'] for d in pm.cluster.resources.get(type="vm")]:
            disco2=[d["volid"] for d in pm.nodes("proxmox1").storage(store).content.get() if d["volid"].split("-")[2]==str(vm)]
            for dis in disco2:
                    #discos.remove(dis)
                    print(dis)
        print(discos)