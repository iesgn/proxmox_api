from pm_gn import *
import sys
argv=sys.argv
pgn=ConectarProxmox()
if len(argv)==3:
    if EsUsuario(pgn,argv[1]) and EsUsuario(pgn,argv[2]):
        resp=input("¿Activar (a) o desactivar (d)?")
        if resp=="a":
            PermisoUsuarioProyecto(pgn,argv[1],argv[2],1)
        elif resp=="d":
            PermisoUsuarioProyecto(pgn,argv[1],argv[2],0)
    elif EsUsuario(pgn,argv[1]) and EsGrupo(pgn,argv[2]):
        resp=input("¿Activar (a) o desactivar (d)?")
        for usuario in GetUsuariosGrupo(pgn,argv[2]):
            if resp=="a":
                PermisoUsuarioProyecto(pgn,argv[1],usuario,1)
            elif resp=="d" and usuario!=argv[1]:
                PermisoUsuarioProyecto(pgn,argv[1],usuario,0)
    else:
        print("Usuario/grupo incorrecto.")
else:
    print("Dos parámetros: usuario y usuario/grupo. Para otorgar permisos del usario sobre los proyectos del usario o del grupo.")
    print("Usuarios:",GetUsuarios(pgn))
    print("Grupos:",GetGrupos(pgn))
