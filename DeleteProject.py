from pm_gn import *
import sys
argv=sys.argv
pgn=ConectarProxmox()
if len(argv)!=2:
    print("Debes indicar el id de un usuario o grupo.")
elif len(argv)==2:
    if EsUsuario(pgn,argv[1]):
        resp=input("Cuidado!!!. Se eliminará todos los recursos del usuario %s. Si estás seguro pulsa (s)!!!!"%argv[1])
        if resp=="s":
            EliminarProyecto(pgn,argv[1])
    elif EsGrupo(pgn,argv[1]):
        resp=input("Cuidado!!!. Se eliminarán todos los recursos de todos los usuarios del grupo %s. Si estás seguro pulsa (s)!!!!"%argv[1])
        if resp=="s":
            for usuario in GetUsuariosGrupo(pgn,argv[1]):
                EliminarProyecto(pgn,usuario)
    else:
        print("Debes indicar el id de un usuario o grupo.")
        print("Usuarios:",GetUsuarios(pgn))
        print("Grupos:",GetGrupos(pgn))