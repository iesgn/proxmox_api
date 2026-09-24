from pm_gn import *
pgn=ConectarProxmox()

# Crea la zona SDN de tipo Simple donde van las VNets de los proyectos de los usuarios.
# Las VNets no tienen subred: son switches aislados (sin DHCP ni enrutado en el host).

if ExisteZona(pgn):
    print("La zona %s ya existe." % ZONA)
else:
    try:
        pgn.cluster.sdn.zones.create(zone=ZONA,type="simple")
        print("Zona %s creada." % ZONA)
        AplicarSDN(pgn)
    except ResourceException as e:
        alert("Problemas al crear la zona %s: %s" % (ZONA,e))
