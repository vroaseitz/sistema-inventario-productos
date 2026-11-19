T=[0,4.5,12,21,29,48,72,89,97,112,137,150]
OFF=4.5; DUR=150; OUT=6.5; END=round(OFF+DUR+OUT,2)
nombres=[("Ingreso","Entra la administradora (usuario de prueba, base temporal)."),
 ("Abrir la jornada","Caja y corte → Abrir jornada. Fondo contado en billetes: $15.000."),
 ("Vender","Código escaneado, código escrito y granel por peso: 0,350 kg × $18.000."),
 ("Cobro mixto","$5.000 en efectivo + $4.500 con tarjeta. Total $9.500."),
 ("Descuento a la línea","10 % con motivo «Cortesía»; paga con $2.000 y recibe $650 de vuelto."),
 ("Catálogo","Producto nuevo y perecible en «Frutos secos y semillas», y la categoría nueva Mascotas."),
 ("Inventario","20 unidades con vencimiento 02-12-2026 y lote ALM-001, en Lotes y vencimientos."),
 ("Clientes","Cliente nuevo con su teléfono de contacto."),
 ("Corte de caja","Esperado $21.350, contado $21.350, diferencia $0. Turno cerrado."),
 ("Compras","Proveedor nuevo y factura F-1001: costo $4.500 → $3.500, +10 unidades, vence 22-12-2026."),
 ("Reportes","Ventas del día, rentabilidad (sin costo se informa, no se inventa) y rotación.")]
glass="background: rgba(15,16,22,.92); backdrop-filter: blur(22px);"
filas=detalles=js=""
for i,(n,d) in enumerate(nombres,1):
    a,b=T[i-1],T[i]; top=150+(i-1)*56; sal=round(b-0.3,2)
    filas+=f'''      <div id="pn-row{i}" class="row" style="top:{top}px">
        <div id="pn-hl{i}" class="hl"></div>
        <span class="num">{i}</span><span class="nom">{n}</span>
      </div>
'''
    detalles+=f'''      <p id="pn-d{i}" class="clip detalle" data-start="{a}" data-duration="{round(b-a,2)}" data-track-index="2">{d}</p>
'''
    js+=f'''    tl.fromTo("#pn-hl{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, ease: "power2.out" }}, {a});
    tl.fromTo("#pn-row{i}", {{ opacity: 0.45 }}, {{ opacity: 1, duration: 0.3 }}, {a});
    tl.fromTo("#pn-hl{i}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.3, immediateRender: false }}, {sal});
    tl.fromTo("#pn-row{i}", {{ opacity: 1 }}, {{ opacity: 0.45, duration: 0.3, immediateRender: false }}, {sal});
    tl.fromTo("#pn-d{i}", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }}, {round(a+0.2,2)});
'''
open("compositions/panel.html","w").write(f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #f3f5f4; }}
    #pn-all {{ position: absolute; inset: 0; }}
    #pn-fondo {{ position: absolute; left: 1530px; top: 40px; width: 370px; height: 1000px; background: #232b28; border-radius: 10px; }}
    #pn-titulo {{ position: absolute; left: 1560px; top: 62px; width: 320px; font-size: 26px; font-weight: 700; line-height: 1.15; }}
    #pn-sub {{ position: absolute; left: 1560px; top: 112px; width: 320px; font-size: 18px; color: #8c958f; }}
    .row {{ position: absolute; left: 1545px; width: 340px; height: 48px; opacity: 0.45; }}
    .hl {{ position: absolute; inset: 0; background: #2f6b45; border-radius: 8px; opacity: 0; }}
    .num {{ position: absolute; left: 14px; top: 11px; width: 26px; height: 26px; border-radius: 13px; background: #3a4541; text-align: center; font-size: 15px; line-height: 26px; font-weight: 700; }}
    .nom {{ position: absolute; left: 54px; top: 10px; font-size: 22px; font-weight: 600; white-space: nowrap; }}
    #pn-prog-fondo {{ position: absolute; left: 1560px; top: 790px; width: 310px; height: 6px; border-radius: 3px; background: #3a4541; }}
    #pn-prog {{ position: absolute; left: 1560px; top: 790px; width: 310px; height: 6px; border-radius: 3px; background: #7fbf95; transform-origin: left center; }}
    .detalle {{ position: absolute; left: 1560px; top: 815px; width: 310px; font-size: 22px; font-weight: 500; line-height: 1.35; color: #ffffff; }}
    #pn-nota {{ position: absolute; left: 1560px; top: 985px; width: 310px; font-size: 14px; line-height: 1.3; color: #8c958f; }}
  </style>
  <div id="root" data-composition-id="panel" data-width="1920" data-height="1080">
    <div id="pn-all">
      <div id="pn-fondo"></div>
      <h2 id="pn-titulo">Prueba de punta a punta</h2>
      <p id="pn-sub">Emporio NaturalSur · POS e Inventario</p>
{filas}      <div id="pn-prog-fondo"></div>
      <div id="pn-prog"></div>
{detalles}      <p id="pn-nota">Base de prueba temporal y usuario ficticio. Sin impresora ni sincronización con Supabase.</p>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#pn-all", {{ opacity: 0, x: 40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.8, ease: "expo.out" }}, 0);
    tl.fromTo("#pn-prog", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {T[-1]-0.5}, ease: "none" }}, 0);
{js}    window.__timelines["panel"] = tl;
  </script>
</template>
''')
cl=""; js=""
for i,(n,_) in enumerate(nombres,1):
    a=round(T[i-1]+0.4,2); d=2.4
    cl+=f'    <div id="ch-{i}" class="clip chip" data-start="{a}" data-duration="{d}" data-track-index="{i+2}"><span class="ch-n">PASO {i}</span><span class="ch-t">{n}</span></div>\n'
    js+=f'''    tl.fromTo("#ch-{i}", {{ opacity: 0, x: -40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.5, ease: "expo.out" }}, {a});
    tl.fromTo("#ch-{i}", {{ opacity: 1, x: 0 }}, {{ opacity: 0, x: -20, duration: 0.3, ease: "power2.in", immediateRender: false }}, {round(a+d-0.3,2)});
'''
open("compositions/capitulos.html","w").write(f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #f3f5f4; }}
    .chip {{ position: absolute; left: 56px; top: 68px; height: 60px; padding: 0 26px 0 20px; border-radius: 12px; {glass} border-left: 6px solid #7fbf95; white-space: nowrap; }}
    .ch-n {{ font-size: 16px; font-weight: 800; letter-spacing: 0.16em; color: #7fbf95; line-height: 60px; margin-right: 16px; }}
    .ch-t {{ font-size: 28px; font-weight: 700; line-height: 60px; }}
  </style>
  <div id="root" data-composition-id="capitulos" data-width="1920" data-height="1080">
{cl}  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js}    window.__timelines["capitulos"] = tl;
  </script>
</template>
''')
stats=[("$9.500","total a cobrar · 3 productos",21.4,3.2),
       ("$5.000 + $4.500","efectivo + tarjeta",24.6,2.8),
       ("−$150","10 % de descuento · motivo Cortesía",35.0,3.6),
       ("$650","de vuelto: pagó con $2.000 por $1.350",43.0,3.2),
       ("Frutos secos y semillas","categoría del producto nuevo · perecible, avisa 7 días antes",62.9,3.2),
       ("Mascotas","categoría nueva, ya en la lista y en el selector",70.2,2.6),
       ("Vence 02-12-2026","lote ALM-001 · 20 unidades",86.0,3.0),
       ("$0","de diferencia: esperado $21.350 = contado $21.350",106.2,3.0),
       ("Distribuidora Sur","proveedor nuevo, con su contacto",113.6,3.0),
       ("$41.650","factura F-1001: $35.000 + IVA $6.650",132.2,3.4)]
sl=""; js=""
for i,(c,l,a,d) in enumerate(stats,1):
    sl+=f'    <div id="st-{i}" class="clip stat" data-start="{a}" data-duration="{d}" data-track-index="{i+2}"><div class="st-c">{c}</div><div class="st-l">{l}</div></div>\n'
    js+=f'''    tl.fromTo("#st-{i}", {{ opacity: 0, y: 36, scale: 0.96 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.7, ease: "expo.out" }}, {a});
    tl.fromTo("#st-{i}", {{ opacity: 1, y: 0 }}, {{ opacity: 0, y: 12, duration: 0.3, ease: "power2.in", immediateRender: false }}, {round(a+d-0.3,2)});
'''
open("compositions/cifras.html","w").write(f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #f3f5f4; }}
    .stat {{ position: absolute; left: 56px; top: 880px; padding: 14px 30px 16px 26px; border-radius: 14px; {glass} border-left: 6px solid #7fbf95; }}
    .st-c {{ font-size: 54px; font-weight: 900; letter-spacing: -0.02em; line-height: 1.05; color: #ffffff; white-space: nowrap; }}
    .st-l {{ font-size: 24px; font-weight: 500; color: #c8cecb; margin-top: 4px; white-space: nowrap; }}
  </style>
  <div id="root" data-composition-id="cifras" data-width="1920" data-height="1080">
{sl}  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js}    window.__timelines["cifras"] = tl;
  </script>
</template>
''')
cam=[(0.3,1.0,1.9,357,275),(4.0,0.6,1,745,500),
 (7.0,0.8,1.7,324,429),(10.2,0.7,1,745,500),
 (12.3,0.9,1.5,600,560),(14.8,0.8,2.0,382,327),(18.8,0.7,2.0,1300,930),(20.6,0.5,1,745,500),
 (21.2,0.8,1.35,744,530),(27.8,0.8,1,745,500),
 (31.8,0.8,1.5,744,533),(39.8,0.8,1.35,744,520),(46.6,0.7,1,745,500),
 (49.8,0.9,1.3,742,563),(62.8,0.8,1.5,745,430),(66.2,0.5,1,745,500),
 (66.8,0.7,1.8,629,491),(70.2,0.6,1.8,500,760),(71.9,0.5,1,745,500),
 (72.4,0.8,1.7,417,245),(77.7,0.7,1.7,647,427),(82.6,0.6,1.7,417,245),(85.9,0.7,1.8,500,350),(88.8,0.5,1,745,500),
 (91.8,0.8,1.7,782,643),(96.7,0.4,1,745,500),
 (99.8,0.8,1.5,682,766),(105.8,0.7,1.9,816,317),(109.0,0.7,1,745,500),
 (111.8,0.7,1.8,448,290),(113.9,0.7,1.8,500,350),(116.0,0.8,1.3,745,350),(122.8,0.7,1.8,780,696),(126.6,0.7,1.3,745,620),(133.8,0.7,1.5,745,300),(136.7,0.5,1,745,500),
 (137.3,0.8,1.3,745,420)]
cam_js=""
for t,d,s,fx,fy in cam:
    x=745-fx*s; y=500-fy*s
    x=min(0,max(1490-1490*s,x)); y=min(0,max(1000-1000*s,y))
    cam_js+=f'      tl.to("#cam", {{ scale: {s}, x: {round(x,1)}, y: {round(y,1)}, duration: {d}, ease: "power2.inOut" }}, {round(OFF+t,2)});\n'
ix=open("index.html").read()
a=ix.index('      tl.to("#cam"'); b=ix.index('      window.__timelines["main"]')
ix=ix[:a]+cam_js+ix[b:]
import re
ix=re.sub(r'(<div id="root" data-composition-id="main" data-start="0" data-duration=")[0-9.]+',r'\g<1>'+str(END),ix)
ix=re.sub(r'(<video[^>]*data-duration=")[0-9.]+',r'\g<1>'+str(DUR),ix)
for host in ("panel","capitulos","cifras"):
    ix=re.sub(r'(id="%s"[^>]*data-start="4.5" data-duration=")[0-9.]+'%host,r'\g<1>'+str(DUR),ix)
ix=re.sub(r'(id="outro"[^>]*data-start=")[0-9.]+(" data-duration=")[0-9.]+',r'\g<1>'+str(OFF+DUR)+r'\g<2>'+str(OUT),ix)
open("index.html","w").write(ix)
# intro / outro
i=open("compositions/intro.html").read(); i=re.sub(r">\d+ pasos<",">11 pasos<",i); open("compositions/intro.html","w").write(i)
o=open("compositions/outro.html").read()
o=re.sub(r'<div class="cifra">\d+</div><div class="rotulo">pasos','<div class="cifra">11</div><div class="rotulo">pasos',o)
o=o.replace('<div class="cifra">5</div><div class="rotulo">problemas','<div class="cifra">6</div><div class="rotulo">problemas')
o=re.sub(r'<b>Pendiente:</b>.*?</div>','<b>Pendiente:</b> aplicar la migración 007 en Supabase, sincronizar clientes, compras y proveedores, y probar la impresora real.</div>',o,flags=re.S)
open("compositions/outro.html","w").write(o)
print("ok",END)
