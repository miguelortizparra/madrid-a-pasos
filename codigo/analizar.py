from pathlib import Path
import json, hashlib, zipfile
import numpy as np
import pandas as pd
import shapefile
import shapely
from shapely.geometry import shape, mapping
from scipy.spatial import cKDTree
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from matplotlib.collections import PatchCollection

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'entregable'; DATA=ROOT/'datos'; (OUT/'mapas').mkdir(exist_ok=True)
for z in ['bancos','demografia']:
    with zipfile.ZipFile(DATA/f'{z}.zip') as f:f.extractall(DATA/z)
def read(p):
    r=shapefile.Reader(str(p),encoding='utf-8')
    return pd.DataFrame([x.as_dict() for x in r.iterRecords()]),[shape(x.__geo_interface__) for x in r.iterShapes()]
b,bg=read(DATA/'bancos/Bancos')
s,sg=read(DATA/'demografia/20260101_estructura_demografica_seccion')
bar,barg=read(DATA/'demografia/20260101_estructura_demografica_barrio')
dis,disg=read(DATA/'demografia/20260101_estructura_demografica_distrito')
for df in [s,bar,dis]:
    for col,width in [('COD_DIS',2),('COD_BAR',3),('COD_SEC',5)]:
        if col in df:df[col]=df[col].str.strip().str.zfill(width)
assert b.ID.nunique()==len(b), 'Revisar ID duplicados antes de continuar'
assert all(g.geom_type=='Point' for g in bg)
assert all(g.is_valid for g in sg), 'Revisar geometrías'
valid=(b.ESTADO=='OPERATIVO').to_numpy()
xy=np.array([[g.x,g.y] for g in bg])[valid]
tree=cKDTree(xy)
polytree=shapely.STRtree(sg)
pairs=polytree.query(shapely.points(xy),predicate='within')
counts=np.bincount(pairs[1],minlength=len(s))
assert len(set(pairs[0]))==len(pairs[0]), 'Solape de secciones'
s['bancos']=counts
s['area_ha']=[g.area/10000 for g in sg]
s['bancos_ha']=s.bancos/s.area_ha
s['pct65']=s.Proporci_1
s['barrio']=s.COD_BAR.map(bar.set_index('COD_BAR').NOMBRE)
s['distrito']=s.COD_DIS.map(dis.set_index('COD_DIS').NOMBRE)
GRID=25
for threshold in [100,150,200]:s[f'cob{threshold}']=np.nan
s['n_muestra']=0
s['dist_p50']=np.nan;s['dist_p90']=np.nan
for i,g in enumerate(sg):
    xmin,ymin,xmax,ymax=g.bounds
    xs=np.arange(np.floor(xmin/GRID)*GRID+GRID/2,xmax,GRID)
    ys=np.arange(np.floor(ymin/GRID)*GRID+GRID/2,ymax,GRID)
    xx,yy=np.meshgrid(xs,ys); q=np.column_stack([xx.ravel(),yy.ravel()])
    q=q[shapely.contains_xy(g,q[:,0],q[:,1])]
    s.loc[i,'n_muestra']=len(q)
    if len(q)<30:continue
    dd=tree.query(q)[0]
    for t in [100,150,200]:s.loc[i,f'cob{t}']=100*np.mean(dd<=t)
    s.loc[i,'dist_p50']=np.median(dd);s.loc[i,'dist_p90']=np.quantile(dd,.9)
    if i%500==0:print('secciones',i,flush=True)
s['elegible']=(s.Densidad>=100)&(s.n_muestra>=30)&s.pct65.notna()
e=s[s.elegible]; qage=float(e.pct65.quantile(.75));qcov=float(e.cob150.quantile(.25))
s['revision']=(s.elegible)&(s.pct65>=qage)&(s.cob150<=80)
for t in [100,200]:
    s[f'revision{t}']=s.elegible&(s.pct65>=qage)&(s[f'cob{t}']<=80)
s['robusta']=s.revision&s.revision100&s.revision200
s.to_csv(OUT/'resultados_secciones.csv',index=False,encoding='utf-8-sig')
tf=Transformer.from_crs(25830,4326,always_xy=True)
from shapely.ops import transform
features=[]
for i,g in enumerate(sg):
    props={k:(None if pd.isna(v) else (v.item() if isinstance(v,np.generic) else v)) for k,v in s.loc[i].items()}
    features.append({'type':'Feature','geometry':mapping(transform(tf.transform,g)),'properties':props})
(OUT/'secciones_resultado.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False),encoding='utf8')
summary={
 'fecha_descarga':'2026-10-02','bancos_registros':len(b),'bancos_operativos':int(valid.sum()),
 'bancos_asignados_seccion':int(counts.sum()),'bancos_fuera_o_en_borde':int(len(xy)-len(pairs[0])),
 'secciones':len(s),'elegibles':len(e),'pct65_q75':qage,'cob150_q25':qcov,
 'revision':int(s.revision.sum()),'robustas':int(s.robusta.sum()),'malla_m':GRID,'umbral_cobertura_pct':80,
 'estados':b.ESTADO.value_counts().to_dict(),
 'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA/'bancos.zip',DATA/'demografia.zip']},
 'mediana_cob150_elegibles':float(e.cob150.median()),
 'candidatos':s[s.revision].sort_values(['robusta','cob150','pct65'],ascending=[False,True,False]).head(12)[['COD_SEC','barrio','distrito','bancos','pct65','cob100','cob150','cob200','robusta','Densidad','n_muestra']].to_dict('records')}
(OUT/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
def polys(g):return list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
def draw(ax,geoms,values=None,cmap='YlOrBr',vmin=None,vmax=None):
    patches=[];vs=[]
    for i,g in enumerate(geoms):
        for pg in polys(g):
            patches.append(Patch(np.asarray(pg.exterior.coords),closed=True))
            if values is not None:vs.append(values[i])
    c=PatchCollection(patches,linewidth=.12,edgecolor='#b8bdc3',cmap=cmap)
    if values is None:c.set_facecolor('#f2f4f5')
    else:c.set_array(np.array(vs,dtype=float));c.set_clim(vmin,vmax)
    ax.add_collection(c);ax.autoscale_view();ax.set_aspect('equal');ax.axis('off');return c
def save(name,title,subtitle,values,cmap,vmin,vmax,label):
    fig,ax=plt.subplots(figsize=(10,10));c=draw(ax,sg,values,cmap,vmin,vmax)
    fig.suptitle(title,fontsize=19,x=.08,ha='left',y=.96)
    fig.text(.08,.91,subtitle,fontsize=10)
    fig.colorbar(c,ax=ax,shrink=.55,pad=.015,label=label)
    fig.text(.08,.04,'Fuente: Geoportal de Madrid · Descarga 02/10/2026 · ETRS89 UTM 30N\nAnálisis exploratorio. La distancia en línea recta no representa un recorrido peatonal.',fontsize=9)
    fig.savefig(OUT/'mapas'/name,dpi=180,bbox_inches='tight');plt.close(fig)
save('01_envejecimiento.png','Dónde vive una mayor proporción de personas mayores','Porcentaje de población de 65 años o más por sección censal · Padrón 01/01/2026',s.pct65.to_numpy(),'YlOrBr',0,50,'Población de 65 años o más (%)')
save('02_proximidad.png','Dónde el inventario queda más lejos','Porcentaje de puntos de una malla de 25 m a un banco registrado a 150 m o menos',s.cob150.to_numpy(),'viridis',0,100,'Muestra territorial con banco cercano (%)')
fig,ax=plt.subplots(figsize=(10,10));draw(ax,sg)
draw(ax,[sg[i] for i in s.index[s.revision]])
for i in s.index[s.revision]:
    for pg in polys(sg[i]):ax.fill(*pg.exterior.xy,color='#c65b2b',alpha=.8)
selected_bounds=np.array([sg[i].bounds for i in s.index[s.revision]])
ax.set_xlim(selected_bounds[:,0].min()-1200,selected_bounds[:,2].max()+1200)
ax.set_ylim(selected_bounds[:,1].min()-1200,selected_bounds[:,3].max()+1200)
for name,g in zip(dis.NOMBRE,disg):
    for pg in polys(g):ax.plot(*pg.exterior.xy,color='#79858c',lw=.4)
    p=g.representative_point()
    if ax.get_xlim()[0]<p.x<ax.get_xlim()[1] and ax.get_ylim()[0]<p.y<ax.get_ylim()[1]:
        ax.text(p.x,p.y,name,fontsize=6,ha='center',color='#42515a')
fig.suptitle('Secciones para revisar sobre el terreno',fontsize=19,x=.08,ha='left',y=.96)
fig.text(.08,.91,f'{int(s.revision.sum())} secciones · Envejecimiento ≥ P75 y proximidad ≤80% en la muestra urbana',fontsize=10)
fig.text(.08,.04,'Naranja: selección exploratoria, no propuesta definitiva de ubicación.\nMuestra urbana: densidad ≥100 hab/ha y al menos 30 puntos de malla. Fuente: Geoportal de Madrid.',fontsize=9)
fig.savefig(OUT/'mapas/03_revision.png',dpi=180,bbox_inches='tight');plt.close(fig)
case=[]
for _,row in s[s.robusta].sort_values(['cob150','pct65'],ascending=[True,False]).iterrows():
    if row.barrio not in [x['barrio'] for x in case]:case.append(row.to_dict())
    if len(case)==3:break
summary['casos']=case
(OUT/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
controls=[]
for n,row in enumerate(case,1):
    i=int(s.index[s.COD_SEC==row['COD_SEC']][0]);g=sg[i];x,y=g.centroid.coords[0]
    rp=g.representative_point();row['lon'],row['lat']=tf.transform(rp.x,rp.y)
    a,b,d,e=g.bounds
    xx,yy=np.meshgrid(np.arange(np.floor(a/GRID)*GRID+GRID,d,GRID),np.arange(np.floor(b/GRID)*GRID+GRID,e,GRID))
    q=np.column_stack([xx.ravel(),yy.ravel()]);q=q[shapely.contains_xy(g,q[:,0],q[:,1])];dd=tree.query(q)[0]
    controls.append({'COD_SEC':row['COD_SEC'],'n_muestra_desplazada':len(q),'cob150_desplazada':100*float(np.mean(dd<=150)),'cob200_desplazada':100*float(np.mean(dd<=200))})
    fig,ax=plt.subplots(figsize=(9,7));draw(ax,sg)
    for pg in polys(g):ax.fill(*pg.exterior.xy,color='#f4d3b4',alpha=.8)
    near=(np.abs(xy[:,0]-x)<800)&(np.abs(xy[:,1]-y)<800)
    ax.scatter(xy[near,0],xy[near,1],s=12,c='#126b70',label='Banco inventariado')
    ax.set_xlim(x-650,x+650);ax.set_ylim(y-500,y+500);ax.legend(loc='lower right')
    fig.suptitle(f"Caso {n} · {row['barrio']} · sección {row['COD_SEC']}",fontsize=16)
    fig.text(.07,.04,f"Población ≥65: {row['pct65']:.1f}% · Muestra a ≤150 m de un banco: {row['cob150']:.1f}%\nContexto geométrico. No se han comprobado recorridos, barreras ni existencia actual.",fontsize=9)
    fig.savefig(OUT/f'mapas/0{n+3}_caso.png',dpi=180,bbox_inches='tight');plt.close(fig)
(OUT/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'control_malla.json').write_text(json.dumps(controls,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
