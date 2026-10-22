from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');h={};exec((L/'trace-r201-dungeon-floor-wall-navigation-20261019.py').read_text().split('nodes={};bycell=')[0],h)
for x,z in [(15750,-42000),(15750,-42500),(16000,-42500),(16000,-42000),(16750,-42000),(17000,-42000),(17250,-42500),(16750,-43000)]:
 ys=[h['plane'](t,x,z)for t in h['floors']];ys=sorted(set(round(y,1)for y in ys if y is not None));print(x,z,[(y,h['blocked'](round(x/250),round(z/250),y))for y in ys])
