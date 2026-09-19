'use strict';
const $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let token=null,user=null,cart=[],view='Inicio',pageNumber=1,renderVersion=0,requestController=new AbortController();
const main=$('#content'),notice=$('#notice');

const SESSION_KEY='belleza.access_token.v1';
function storedToken(){try{return sessionStorage.getItem(SESSION_KEY);}catch{return null;}}
function rememberToken(value){try{sessionStorage.setItem(SESSION_KEY,value);}catch{say('El navegador no permite conservar la sesión al refrescar.');}}
function clearSession(){token=null;user=null;cart=[];try{sessionStorage.removeItem(SESSION_KEY);}catch{}}
async function start(){
  const saved=storedToken();
  if(!saved)return render();
  main.innerHTML='<p>Comprobando tu sesión…</p>';
  $('#nav').innerHTML='';
  $('#account').textContent='';
  try{
    const r=await fetch('/api/v1/auth/perfil',{headers:{Authorization:'Bearer '+saved},cache:'no-store'});
    if(r.status===401){clearSession();view='Ingresar';say('Tu sesión terminó. Inicia sesión nuevamente.');return render();}
    if(!r.ok)throw new Error('No fue posible comprobar la sesión.');
    const b=await r.json();
    if(!b.success||!b.data||!['cliente','personal','administrador'].includes(b.data.rol))throw new Error('Respuesta de sesión inválida.');
    token=saved;user=b.data;
    view=user.rol==='personal'?'Mi agenda':user.rol==='administrador'?'Reportes':'Servicios';
    await render();
  }catch{
    // Un fallo de red no equivale a una sesión revocada. Conservar para reintentar.
    token=null;user=null;
    main.innerHTML='<p>No se pudo comprobar tu sesión. Revisa la conexión e inténtalo otra vez.</p><button id="retrySession">Reintentar</button><button id="discardSession" class="secondary">Volver al ingreso</button>';
    $('#retrySession').onclick=()=>start();
    $('#discardSession').onclick=()=>{clearSession();view='Ingresar';render();};
  }
}

function operationKey(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');}
function say(s){notice.textContent=s;}
async function api(path,method='GET',data){const r=await fetch('/api/v1'+path,{method,signal:requestController.signal,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(data!==undefined?{'Content-Type':'application/json'}:{})},body:data===undefined?undefined:JSON.stringify(data)});const b=await r.json();if(!r.ok){if(r.status===401&&token){clearSession();navigation();say('Tu sesión terminó. Inicia sesión nuevamente.');}throw new Error(b.message||'No fue posible completar la operación.');}return b;}
function field(name,label,type='text',options){return {name,label,type,options};}
function formFields(fields,values={}){return fields.map(f=>`<label for="f_${esc(f.name)}">${esc(f.label)}</label>`+(f.type==='select'?`<select id="f_${esc(f.name)}" name="${esc(f.name)}">${f.options.map(o=>`<option value="${esc(o.value??o)}" ${String(values[f.name])===String(o.value??o)?'selected':''}>${esc(o.label??o)}</option>`).join('')}</select>`:`<input id="f_${esc(f.name)}" name="${esc(f.name)}" type="${esc(f.type)}" value="${esc(values[f.name]??'')}" ${f.type==='password'?'autocomplete="current-password"':''} ${f.optional?'':'required'} ${f.type==='number'?'step="1"':''}>`)).join('');}
function values(form,fields){const d=Object.fromEntries(new FormData(form));fields.forEach(f=>{if(f.type==='number')d[f.name]=Number(d[f.name]);if(f.optional&&!d[f.name])d[f.name]=null;});return d;}
function modal(title,fields,initial,submit){const submitButton=$('#modalForm').querySelector('[type="submit"]');submitButton.disabled=false;submitButton.textContent='Guardar';$('#modalTitle').textContent=title;$('#fields').innerHTML=formFields(fields,initial);$('#formError').textContent='';$('#modal').showModal();$('#modalForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await submit(values(e.target,fields));$('#modal').close();await render();}catch(err){$('#formError').textContent=err.message;}finally{b.disabled=false;}};}
$('#closeModal').onclick=()=>$('#modal').close();
async function action(fn){try{await fn();}catch(e){if(e.name!=='AbortError')say(e.message);}}
function go(next){view=next;pageNumber=1;say('');render();}
function navigation(){
 const primary=['Inicio','Servicios','Productos','Promociones',...(!user?['Registrarme']:[])];
 const workspace=user?['Mi cuenta',...(user.rol==='cliente'?['Mis citas','Recordatorios','Carrito','Mis pedidos','Mis puntos','Mi suscripción']:user.rol==='personal'?['Mi agenda','Recordatorios']:['Usuarios','Clientes','Citas admin','Servicios admin','Horarios','Inventario','Movimientos de inventario','Pedidos admin','Promociones admin','Puntos admin','Planes suscripción','Suscripciones admin','Pagos suscripción','Reportes'])]:['Ingresar','Registrarme'];
 const buttons=items=>items.map(i=>`<button type="button" data-view="${esc(i)}" class="${view===i?'selected':''}" ${view===i?'aria-current="page"':''}>${esc(i)}</button>`).join('');
 $('#nav').innerHTML='<div class="primary-nav">'+buttons(primary)+'</div>'+(user?'<div class="workspace-nav"><span class="workspace-label">Tu espacio</span>'+buttons(workspace)+'</div>':'');
 $('#nav').classList.remove('open');$('#menuToggle').setAttribute('aria-expanded','false');
 $('#nav').querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>go(b.dataset.view));
 $('#account').innerHTML=user?`<span>${esc(user.nombre)}</span><button id="logout" class="secondary">Salir</button>`:'<button type="button" data-go="Ingresar" class="secondary">Ingresar</button>';
 if(user)$('#logout').onclick=()=>action(async()=>{try{await api('/auth/logout','POST');}finally{clearSession();pendingService=null;view='Inicio';await render();}});
}
function table(rows,fields,buttons){if(!rows.length)return '<p class="muted">No hay registros para mostrar.</p>';return `<div class="table"><table><thead><tr>${fields.map(([k,t])=>`<th>${esc(t)}</th>`).join('')}${buttons?'<th>Acciones</th>':''}</tr></thead><tbody>${rows.map(r=>`<tr>${fields.map(([k])=>`<td>${esc(r[k])}</td>`).join('')}${buttons?`<td>${buttons(r)}</td>`:''}</tr>`).join('')}</tbody></table></div>`;}
function bind(selector,fn){main.querySelectorAll(selector).forEach(b=>b.onclick=()=>action(async()=>{b.disabled=true;try{await fn(b);}finally{b.disabled=false;}}));}
function pager(meta){if(!meta)return;main.insertAdjacentHTML('beforeend',`<div class="actions"><button id="prev" class="secondary" ${pageNumber<=1?'disabled':''}>Anterior</button><span>Página ${pageNumber}${meta.paginas!==undefined?' de '+Math.max(1,meta.paginas):''}</span><button id="next" class="secondary" ${(meta.paginas!==undefined?pageNumber>=meta.paginas:meta.cantidad<20)?'disabled':''}>Siguiente</button></div>`);$('#prev').onclick=()=>{pageNumber--;render();};$('#next').onclick=()=>{pageNumber++;render();};}
function dateToday(){return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Guatemala',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
async function render(){const version=++renderVersion;requestController.abort();requestController=new AbortController();navigation();main.innerHTML='<p class="loading" role="status">Cargando…</p>';document.title=(view==='Inicio'?'Un momento para ti':view)+' · Belleza Integral';try{await screens[view]();}catch(e){if(version!==renderVersion||e.name==='AbortError')return;main.innerHTML='<div class="empty-state"><p>No fue posible cargar esta sección.</p><button id="retryView">Reintentar</button></div>';$('#retryView').onclick=()=>render();say(e.message);}}
const screens={};
const serviceCache=new Map();
let pendingService=null;
const serviceSymbol='<svg viewBox="0 0 60 80" fill="none" aria-hidden="true"><path d="M20 6h20v22H20zM17 30h26a6 6 0 0 1 6 6v34a6 6 0 0 1-6 6H17a6 6 0 0 1-6-6V36a6 6 0 0 1 6-6Z" stroke-width="1.5"/><path d="m30 43 3 7 7 3-7 3-3 7-3-7-7-3 7-3z" stroke-width="1.2"/><path d="M25 9v16m5-16v16m5-16v16"/></svg>';
function collectServices(items){items.forEach(s=>serviceCache.set(Number(s.id),s));}
function bindReservations(){bind('[data-reserve]',async b=>{const id=Number(b.dataset.reserve);if(!user){pendingService=id;view='Ingresar';say('Inicia sesión para continuar con tu reserva.');return render();}if(user.rol!=='cliente')throw new Error('Las reservas se realizan desde una cuenta cliente.');await reserva(id);});}
function serviceCard(s,preview=false){
 if(preview)return `<article class="service-preview"><span class="badge">${esc(s.categoria)}</span><h3>${esc(s.nombre)}</h3><p>${esc(s.descripcion||'Consulta los horarios y elige tu próxima cita.')}</p><div class="service-end"><p class="price">Q ${esc(s.precio)}<small>${esc(s.duracion_min)} minutos</small></p><button data-reserve="${Number(s.id)}">Reservar <span aria-hidden="true">↗</span></button></div></article>`;
 return `<article class="service-card"><div class="service-visual">${serviceSymbol}</div><div class="service-body"><span class="badge">${esc(s.categoria)}</span><h2>${esc(s.nombre)}</h2><p class="description">${esc(s.descripcion||'Consulta los horarios y elige tu próxima cita.')}</p><div class="service-meta"><span class="duration">${esc(s.duracion_min)} minutos</span><p class="price">Q ${esc(s.precio)}</p></div><button data-reserve="${Number(s.id)}">Reservar este servicio <span aria-hidden="true">↗</span></button></div></article>`;
}
screens.Inicio=async()=>{
 main.innerHTML=`<section class="home-hero" aria-labelledby="homeTitle"><div class="hero-copy"><span class="eyebrow">Belleza integral · tu espacio</span><h1 id="homeTitle">Un momento para ti.<br><em>Para sentirte bien.</em></h1><p>Haz espacio para cuidarte. Explora nuestros servicios y encuentra el momento para tu próxima cita.</p><div class="hero-buttons"><button data-go="Servicios">Reservar una cita <span aria-hidden="true">↗</span></button><button class="secondary" data-how>Cómo reservar</button></div><div class="hero-footnote"><span aria-hidden="true">✧</span><span>Elige tu servicio, profesional y horario.</span></div></div><div class="hero-art"><img src="/visor/salon.svg" width="620" height="650" alt="Ilustración de un tocador con espejo, esmalte y una planta"><div class="art-caption"><span>TU BELLEZA, NUESTRA PASIÓN</span><strong>El cuidado empieza contigo.</strong></div></div></section><div class="benefit-strip"><div><b aria-hidden="true">01</b>Reserva desde donde estés</div><div><b aria-hidden="true">02</b>Elige a tu profesional</div><div><b aria-hidden="true">03</b>Gestiona tus citas</div></div><section class="home-services" aria-labelledby="servicesTitle"><div class="section-intro"><span class="eyebrow">Nuestro catálogo</span><h2 id="servicesTitle">Encuentra tu<br>próximo cuidado.</h2><p>Consulta precios y duración antes de reservar. Los horarios disponibles se muestran al elegir a tu profesional.</p><button class="text-link" data-go="Servicios">Ver todos los servicios <span aria-hidden="true">→</span></button></div><div id="featuredServices" class="service-list" aria-live="polite"><p class="loading">Cargando servicios…</p></div></section><section class="how-section" id="how" aria-labelledby="howTitle"><div class="how-heading"><span class="eyebrow">Así de sencillo</span><h2 id="howTitle" tabindex="-1">Tu próxima cita, en tres pasos.</h2></div><div class="steps"><div><span class="step-number">01</span><h3>Elige tu servicio</h3><p>Encuentra en el catálogo el cuidado que buscas y consulta sus detalles.</p></div><div><span class="step-number">02</span><h3>Encuentra tu momento</h3><p>Ingresa a tu cuenta, elige un profesional y consulta sus horarios.</p></div><div><span class="step-number">03</span><h3>Revisa tu confirmación</h3><p>La reserva queda pendiente. Consulta la confirmación del profesional en Mis citas.</p></div></div></section><section class="final-cta"><span class="eyebrow">A tu ritmo</span><h2>Dedícate ese momento.</h2><p>Tu próxima cita está a unos pasos.</p><button data-go="Servicios">Explorar servicios <span aria-hidden="true">↗</span></button></section>`;
 main.querySelector('[data-how]').onclick=()=>{$('#howTitle').focus();$('#how').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});};
 try{const r=await api('/servicios?pagina=1&limite=3');collectServices(r.data);$('#featuredServices').innerHTML=r.data.length?r.data.map(s=>serviceCard(s,true)).join(''):'<div class="empty-state"><h3>Estamos preparando el catálogo.</h3><p>Vuelve pronto para consultar los servicios disponibles.</p></div>';bindReservations();}
 catch(e){if(e.name==='AbortError')throw e;$('#featuredServices').innerHTML='<div class="empty-state"><p>No pudimos consultar los servicios.</p><button data-go="Inicio" class="secondary">Reintentar</button></div>';}
};
screens.Servicios=async()=>{
 const r=await api('/servicios?pagina='+pageNumber);collectServices(r.data);
 main.innerHTML='<div class="page-heading"><div><span class="eyebrow">Elige tu próximo cuidado</span><h1>Servicios para ti.</h1><p>Consulta los detalles y reserva el horario que mejor se adapte a tu día.</p></div><p class="catalog-hint">Precios en quetzales.<br>Horarios según disponibilidad.</p></div>'+(r.data.length?'<div class="catalog-grid">'+r.data.map(s=>serviceCard(s)).join('')+'</div>':'<div class="empty-state"><h2>No hay servicios en esta página.</h2><p>Consulta la página anterior o vuelve más tarde.</p></div>');
 bindReservations();pager(r.meta);
};
async function reserva(service){
 view='Servicios';navigation();
 const people=(await api('/personal')).data;
 const selected=serviceCache.get(Number(service));
 main.innerHTML=`<div class="page-heading"><div><span class="eyebrow">Tu próxima cita</span><h1>Encuentra tu momento.</h1><p>Selecciona al profesional y consulta sus horarios antes de reservar.</p></div><button class="secondary" data-go="Servicios">Volver al catálogo</button></div><div class="booking-layout"><form id="search" class="panel">${formFields([field('personal_id','Profesional','select',people.map(p=>({value:p.id,label:p.nombre}))),field('fecha','Fecha','date')],{fecha:dateToday()})}<div class="actions"><button ${people.length?'':'disabled'}>Consultar horarios</button></div>${people.length?'':'<p>No hay profesionales disponibles en este momento.</p>'}</form><aside class="booking-summary"><span class="eyebrow">Tu selección</span><h2>${esc(selected?.nombre||'Servicio seleccionado')}</h2>${selected?`<p>${esc(selected.duracion_min)} minutos</p><div class="price">Q ${esc(selected.precio)}</div>`:''}<p>La reserva quedará pendiente de confirmación del profesional. Podrás consultarla en Mis citas.</p></aside></div><div id="slots" class="slots" aria-live="polite"></div>`;
 $('#f_fecha').min=dateToday();
 $('#search').onsubmit=e=>{e.preventDefault();action(async()=>{
 const d=Object.fromEntries(new FormData(e.target)),submit=e.submitter;submit.disabled=true;$('#slots').innerHTML='<p>Consultando horarios…</p>';
 try{const r=await api(`/disponibilidad?personal_id=${d.personal_id}&servicio_id=${service}&fecha=${d.fecha}`);if(!$('#search')||$('#f_fecha').value!==d.fecha||$('#f_personal_id').value!==d.personal_id)return;
 $('#slots').innerHTML=r.data.horarios.length?'<p class="slot-help" style="flex-basis:100%">Elige un horario para enviar tu reserva.</p>'+r.data.horarios.map(h=>`<button data-hour="${h.hora_inicio}">${h.hora_inicio} – ${h.hora_fin}</button>`).join(''):'<p>No hay horarios disponibles. Prueba con otra fecha o profesional.</p>';
 bind('[data-hour]',async b=>{await api('/citas','POST',{personal_id:Number(d.personal_id),servicio_id:service,fecha:d.fecha,hora:b.dataset.hour});view='Mis citas';say('Tu cita quedó pendiente de confirmación.');await render();});
 }catch(err){if(err.name!=='AbortError'&&$('#slots'))$('#slots').innerHTML='<p>No pudimos consultar los horarios. Intenta de nuevo.</p>';throw err;}finally{submit.disabled=false;}
 });};
 // No ofrecer horarios obtenidos para una selección anterior.
 $('#search').onchange=()=>{$('#slots').innerHTML='';};
}
function authScreen(register){const fields=register?[field('nombre','Nombre'),field('email','Correo','email'),field('password','Contraseña','password')]:[field('identificador','Correo o teléfono'),field('password','Contraseña','password')];main.innerHTML=`<h1>${register?'Crea tu cuenta':'Bienvenida de nuevo'}</h1><form id="authForm" class="panel">${formFields(fields)}<div class="actions"><button>${register?'Registrarme':'Ingresar'}</button></div></form>`;$('#authForm').onsubmit=e=>{e.preventDefault();action(async()=>{const b=e.submitter;b.disabled=true;try{const r=await api(register?'/auth/registro':'/auth/login','POST',values(e.target,fields));if(register){view='Ingresar';say('Cuenta creada. Ya puedes iniciar sesión.');}else{token=r.data.access_token;user=r.data.usuario;rememberToken(token);view=user.rol==='personal'?'Mi agenda':user.rol==='administrador'?'Reportes':'Servicios';say('');if(user.rol==='cliente'&&pendingService!==null){const selected=pendingService;pendingService=null;await reserva(selected);return;}}await render();}finally{b.disabled=false;}});};}
screens.Ingresar=()=>authScreen(false);screens.Registrarme=()=>authScreen(true);
function readableDate(value){const [y,m,d]=String(value).split('-').map(Number);if(!y||!m||!d)return String(value);return new Intl.DateTimeFormat('es-GT',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(Date.UTC(y,m-1,d)));}
function appointmentFuture(c){return new Date(`${c.fecha}T${String(c.hora).slice(0,5)}:00-06:00`).getTime()>Date.now();}
const statusText={pendiente:'Pendiente',confirmada:'Confirmada',cancelada:'Cancelada',completada:'Completada'};
screens['Mi cuenta']=async()=>{
 const r=await api('/auth/perfil'),p=r.data;
 const initials=String(p.nombre).trim().split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase();
 main.innerHTML=`<div class="page-heading"><div><span class="eyebrow">Tu espacio personal</span><h1>Mi cuenta</h1><p>Mantén tus datos al día y gestiona el acceso a tu cuenta.</p></div></div><div class="account-layout"><article class="profile-card"><span class="profile-avatar" aria-hidden="true">${esc(initials)}</span><h2>${esc(p.nombre)}</h2><span class="badge">${esc(p.rol==='cliente'?'Cliente':p.rol==='personal'?'Profesional':'Administración')}</span>${p.rol==='cliente'?`<div class="profile-points"><span>Mis puntos</span><strong>${esc(p.puntos??0)}</strong><button class="text-link" data-go="Mis puntos">Consultar movimientos →</button></div>`:''}</article><div class="account-panels"><section class="card"><div class="section-title"><h2>Datos de contacto</h2><button id="edit" class="secondary">Editar datos</button></div><dl class="profile-details"><div><dt>Nombre</dt><dd>${esc(p.nombre)}</dd></div><div><dt>Correo electrónico</dt><dd>${esc(p.email||'No registrado')}</dd></div><div><dt>Teléfono</dt><dd>${esc(p.telefono||'No registrado')}</dd></div></dl><p class="muted small-copy">Puedes ingresar con tu correo o teléfono registrado.</p></section><section class="card"><span class="eyebrow">Acceso a tu cuenta</span><h2>Contraseña y sesión</h2><p class="muted small-copy">Al cambiar la contraseña tendrás que iniciar sesión nuevamente. Refrescar la página conserva una sesión que todavía está vigente.</p><button id="password" class="secondary">Cambiar contraseña</button></section></div></div>`;
 $('#edit').onclick=()=>{
  modal('Editar mis datos',[field('nombre','Nombre'),{...field('email','Correo electrónico','email'),optional:true},{...field('telefono','Teléfono','tel'),optional:true}],p,async d=>{const updated=await api('/auth/perfil','PATCH',d);user={...user,...updated.data};navigation();say('Tus datos se actualizaron correctamente.');});
  $('#f_nombre').autocomplete='name';$('#f_email').autocomplete='email';$('#f_telefono').autocomplete='tel';
  $('#fields').insertAdjacentHTML('beforeend','<p class="small-copy muted">Conserva al menos un correo o teléfono para ingresar a tu cuenta.</p>');
 };
 $('#password').onclick=()=>{
  modal('Cambiar contraseña',[field('actual','Contraseña actual','password'),field('nueva','Nueva contraseña','password'),field('confirmacion','Repetir nueva contraseña','password')],{},async d=>{if(d.nueva!==d.confirmacion)throw new Error('Las contraseñas nuevas no coinciden.');await api('/auth/password','PATCH',{actual:d.actual,nueva:d.nueva});clearSession();view='Ingresar';say('Contraseña actualizada. Inicia sesión nuevamente.');});
  for(const id of ['#f_nueva','#f_confirmacion']){$(id).autocomplete='new-password';$(id).minLength=8;$(id).maxLength=128;}
  $('#fields').insertAdjacentHTML('beforeend','<p class="small-copy muted">Usa entre 8 y 128 caracteres. Se cerrarán tus sesiones anteriores.</p>');
 };
};
screens['Mis citas']=async()=>{
 const r=await api('/citas/mias?pagina='+pageNumber);
 main.innerHTML='<div class="page-heading"><div><span class="eyebrow">Tu agenda de cuidado</span><h1>Mis citas</h1><p>Consulta el estado de tus reservas y organiza tu próximo momento.</p></div><button data-go="Servicios">Reservar otra cita ↗</button></div>'+(r.data.length?'<div class="appointment-list">'+r.data.map(c=>{
  const status=statusText[c.estado]||c.estado,allowed=['pendiente','confirmada'].includes(c.estado)&&appointmentFuture(c);
  return `<article class="appointment-card" aria-label="Cita ${Number(c.id)}"><div class="appointment-heading"><span class="appointment-id">CITA #${Number(c.id)}</span><span class="status-pill status-${Object.hasOwn(statusText,c.estado)?c.estado:'otro'}">${esc(status)}</span></div><div class="appointment-body"><div><h2>${esc(c.servicio)}</h2><dl class="appointment-details"><div><dt>Fecha</dt><dd><time datetime="${esc(c.fecha)}">${esc(readableDate(c.fecha))}</time></dd></div><div><dt>Hora · Guatemala</dt><dd>${esc(String(c.hora).slice(0,5))}</dd></div>${c.duracion_min?`<div><dt>Duración</dt><dd>${esc(c.duracion_min)} minutos</dd></div>`:''}${c.profesional?`<div><dt>Profesional</dt><dd>${esc(c.profesional)}</dd></div>`:''}</dl></div><div class="appointment-actions">${allowed?`<button data-change="${Number(c.id)}">Reprogramar</button><button class="secondary" data-cancel="${Number(c.id)}">Cancelar cita</button>`:'<span class="muted small-copy">'+(['pendiente','confirmada'].includes(c.estado)?'El horario de esta cita ya comenzó.':'Esta cita forma parte de tu historial.')+'</span>'}</div></div>${c.estado==='pendiente'?'<p class="appointment-note">Pendiente de confirmación del profesional.</p>':''}</article>`;
 }).join('')+'</div>':'<div class="empty-state"><h2>No hay citas en esta página.</h2><p>Explora los servicios para reservar tu próximo cuidado.</p><button data-go="Servicios">Ver servicios</button></div>');
 bind('[data-change]',b=>openReschedule(r.data.find(c=>c.id===Number(b.dataset.change))));
 bind('[data-cancel]',async b=>{const c=r.data.find(x=>x.id===Number(b.dataset.cancel));if(confirm(`¿Cancelar la cita #${c.id} del ${readableDate(c.fecha)} a las ${c.hora}?`)){await api('/citas/'+c.id+'/cancelar','PATCH');say('La cita se canceló correctamente.');await render();}});
 pager(r.meta);
};
let rescheduleState=null;
$('#modal').addEventListener('close',()=>{if(rescheduleState){rescheduleState.version++;rescheduleState=null;}$('#closeModal').disabled=false;});
$('#modal').addEventListener('cancel',e=>{if(rescheduleState?.saving)e.preventDefault();});
async function openReschedule(cita){
 const dialog=$('#modal'),state={version:0,selected:null,saving:false};rescheduleState=state;
 const save=$('#modalForm').querySelector('[type="submit"]');
 $('#modalTitle').textContent='Reprogramar cita';$('#formError').textContent='';
 $('#fields').innerHTML=`<div class="reschedule-current"><span class="eyebrow">Cita #${Number(cita.id)}</span><strong>${esc(cita.servicio)}</strong><p>Actual: ${esc(readableDate(cita.fecha))} · ${esc(cita.hora)}</p></div><label for="rescheduleDate">Nueva fecha</label><input id="rescheduleDate" type="date" required min="${dateToday()}" value="${esc(cita.fecha)}"><button id="loadReschedule" type="button" class="secondary reschedule-load">Consultar horarios</button><p class="small-copy muted">Selecciona un horario. La cita volverá a pendiente y necesitará una nueva confirmación.</p><div id="rescheduleSlots" class="reschedule-slots" role="group" aria-label="Horarios disponibles" aria-live="polite"></div><p id="rescheduleSelection" class="small-copy"></p>`;
 save.disabled=true;save.textContent='Guardar cambio';dialog.showModal();
 const current=()=>rescheduleState===state&&dialog.open;
 const clear=()=>{state.selected=null;save.disabled=true;$('#rescheduleSelection').textContent='';};
 async function load(){
  const date=$('#rescheduleDate').value,version=++state.version;clear();$('#formError').textContent='';$('#rescheduleSlots').innerHTML='<p>Consultando horarios…</p>';
  if(!date||!$('#rescheduleDate').checkValidity()){$('#rescheduleSlots').innerHTML='<p>Elige una fecha válida desde hoy.</p>';return;}
  try{
   const r=await api(`/citas/${Number(cita.id)}/disponibilidad?fecha=${encodeURIComponent(date)}`);
   if(!current()||state.version!==version||$('#rescheduleDate').value!==date)return;
   $('#rescheduleSlots').innerHTML=r.data.horarios.length?r.data.horarios.map((h,i)=>{const same=date===cita.fecha&&h.hora_inicio===String(cita.hora).slice(0,5);return `<label class="slot-choice ${same?'current-slot':''}" for="changeSlot${i}"><input type="radio" name="newSlot" id="changeSlot${i}" value="${esc(h.hora_inicio)}" ${same?'disabled':''}><span>${esc(h.hora_inicio)}–${esc(h.hora_fin)}${same?' · Actual':''}</span></label>`;}).join(''):'<p>No hay horarios disponibles para esta fecha. Prueba con otro día.</p>';
   $('#rescheduleSlots').querySelectorAll('input').forEach(input=>input.onchange=()=>{if(!current()||state.version!==version)return;state.selected={fecha:date,hora:input.value};save.disabled=false;$('#rescheduleSelection').textContent=`Nuevo horario: ${readableDate(date)} · ${input.value}`;});
  }catch(e){
   if(!current()||state.version!==version)return;
   $('#rescheduleSlots').innerHTML='<p>No pudimos obtener horarios. Puedes consultar de nuevo.</p>';$('#formError').textContent=e.message;
   if(!user){dialog.close();view='Ingresar';render();}
  }
 }
 $('#rescheduleDate').onchange=load;$('#loadReschedule').onclick=load;
 $('#modalForm').onsubmit=async e=>{
  e.preventDefault();if(!current()||state.saving||!state.selected||state.selected.fecha!==$('#rescheduleDate').value)return;
  state.saving=true;save.disabled=true;$('#closeModal').disabled=true;$('#rescheduleDate').disabled=true;$('#loadReschedule').disabled=true;
  $('#rescheduleSlots').querySelectorAll('input').forEach(input=>input.disabled=true);
  try{await api('/citas/'+cita.id+'/reprogramar','PATCH',state.selected);dialog.close();say('Cita reprogramada. Quedó pendiente de confirmación.');await render();}
  catch(e){if(!user){dialog.close();view='Ingresar';say(e.message);await render();}else if(current()){clear();$('#formError').textContent=e.message;$('#rescheduleSlots').innerHTML='<p>Consulta los horarios de nuevo antes de volver a guardar. Si hubo un fallo de conexión, revisa Mis citas para comprobar el resultado.</p>';}}
  finally{state.saving=false;$('#closeModal').disabled=false;if(current()){$('#rescheduleDate').disabled=false;$('#loadReschedule').disabled=false;}}
 };
 await load();
}
screens['Mi agenda']=async()=>{main.innerHTML='<h1>Mi agenda</h1><div class="toolbar"><label>Fecha<input id="agendaDate" type="date" value="'+dateToday()+'"></label><button id="loadAgenda">Consultar</button></div><div id="agendaTable"></div>';const load=async()=>{const r=await api('/agenda?fecha='+$('#agendaDate').value);$('#agendaTable').innerHTML=table(r.data,[['hora','Hora'],['cliente','Cliente'],['servicio','Servicio'],['estado','Estado']],c=>c.estado==='pendiente'?`<button data-state="confirmada" data-id="${c.id}">Confirmar</button>`:c.estado==='confirmada'?`<button data-state="completada" data-id="${c.id}">Completar</button>`:'');bind('[data-state]',async b=>{await api('/agenda/'+b.dataset.id+'/estado','PATCH',{estado:b.dataset.state});await load();});};$('#loadAgenda').onclick=()=>action(load);await load();};
const cartStorageKey=()=> 'belleza.cart.v1.'+user.id;
function loadCart(){if(!user)return;try{const data=JSON.parse(sessionStorage.getItem(cartStorageKey())||'[]');cart=Array.isArray(data)?data.filter(x=>Number.isInteger(x.producto_id)&&Number.isInteger(x.cantidad)&&x.cantidad>0&&x.cantidad<=10000).slice(0,50):[];}catch{cart=[];}}
function saveCart(){if(user)try{sessionStorage.setItem(cartStorageKey(),JSON.stringify(cart));}catch{say('El navegador no permite conservar el carrito al recargar.');}}
function quetzales(value){return 'Q '+Number(value).toFixed(2);}
async function saleCatalog(){let result=[],page=1;while(true){const r=await api('/productos?pagina='+page);result.push(...r.data);if(!r.meta||page>=r.meta.paginas)break;page++;}return result;}
screens.Productos=async()=>{const r=await api('/productos?pagina='+pageNumber);main.innerHTML='<h1>Productos para ti</h1><p>Compras de demostración, sin cobros reales.</p><div class="grid">'+r.data.map(p=>`<article class="card"><span class="badge">${esc(p.categoria)}</span><h2>${esc(p.nombre)}</h2><p>${esc(p.descripcion||'')}</p><p class="price">${quetzales(p.precio)}</p><p>${esc(p.stock)} disponibles</p><button data-add="${p.id}" ${!p.stock?'disabled':''}>${p.stock?'Agregar al carrito':'Agotado'}</button></article>`).join('')+'</div>'+(r.data.length?'':'<p class="empty-state">No hay productos disponibles.</p>');bind('[data-add]',b=>{if(!user){view='Ingresar';say('Inicia sesión como cliente para comprar.');return render();}if(user.rol!=='cliente'){say('Las compras están disponibles para cuentas de cliente.');return;}loadCart();const p=r.data.find(p=>p.id===Number(b.dataset.add));const item=cart.find(x=>x.producto_id===p.id);if((item?.cantidad||0)>=Math.min(p.stock,10000)){say('Ya agregaste las existencias disponibles de este producto.');return;}if(!item&&cart.length>=50){say('El pedido admite hasta 50 productos diferentes.');return;}if(item)item.cantidad++;else cart.push({producto_id:p.id,cantidad:1});saveCart();say('Producto agregado. Puedes revisarlo en Carrito.');});pager(r.meta);};
let checkoutKey=null,checkoutFingerprint=null;
screens.Carrito=async()=>{loadCart();if(!cart.length){main.innerHTML='<h1>Tu carrito</h1><p class="empty-state">Tu carrito está vacío.</p><button data-go="Productos">Explorar productos</button>';return;}
const products=await saleCatalog();let total=0,invalid=false;
const rows=cart.map(item=>{const p=products.find(p=>p.id===item.producto_id);const unavailable=!p||p.stock<item.cantidad;invalid ||= unavailable;const subtotal=p?Math.round(Number(p.precio)*100)*item.cantidad:0;total+=subtotal;return `<article class="card"><h2>${esc(p?.nombre||'Producto no disponible')}</h2><p>${p?quetzales(p.precio)+' por unidad':'Retira este producto para continuar.'}</p><label>Cantidad <input aria-label="Cantidad de ${esc(p?.nombre||item.producto_id)}" data-quantity="${item.producto_id}" type="number" min="1" max="${Math.min(p?.stock||1,10000)}" step="1" value="${item.cantidad}"></label><p>Subtotal: ${quetzales(subtotal/100)}</p>${unavailable?'<p role="alert">Existencias insuficientes o producto no disponible. Ajusta la cantidad o retíralo.</p>':''}<button class="secondary" data-remove="${item.producto_id}">Quitar</button></article>`;}).join('');
main.innerHTML='<h1>Tu carrito</h1>'+rows+`<p class="price">Total estimado: ${quetzales(total/100)}</p><p>El servidor valida el precio y las existencias al confirmar. No se realizan cobros.</p><button id="checkout" ${invalid?'disabled':''}>Continuar con el pedido</button>`;
bind('[data-remove]',b=>{cart=cart.filter(x=>x.producto_id!==Number(b.dataset.remove));saveCart();return render();});
main.querySelectorAll('[data-quantity]').forEach(input=>input.onchange=()=>{const q=Number(input.value),item=cart.find(x=>x.producto_id===Number(input.dataset.quantity));if(!Number.isInteger(q)||q<1||q>Number(input.max)){input.value=item.cantidad;say('Introduce una cantidad entera dentro de las existencias disponibles.');return;}item.cantidad=q;saveCart();render();});
$('#checkout').onclick=()=>{modal('Confirmar pedido de demostración',[field('nombre_entrega','Nombre de quien recibe'),field('telefono_entrega','Teléfono'),field('direccion_entrega','Dirección'),field('metodo_pago','Método de pago (demostración)','select',[{value:'efectivo',label:'Efectivo'},{value:'tarjeta_simulada',label:'Tarjeta ficticia (sin cobro)'}])],{nombre_entrega:user.nombre,telefono_entrega:user.telefono||'',metodo_pago:'efectivo'},async d=>{if(!/^\+?[0-9]{8,15}$/.test(d.telefono_entrega))throw Error('Introduce un teléfono de 8 a 15 dígitos.');const body={...d,items:cart.map(({producto_id,cantidad})=>({producto_id,cantidad}))};if(d.metodo_pago==='tarjeta_simulada')body.tarjeta_ultimos4='0000';const fingerprint=JSON.stringify(body);if(checkoutFingerprint!==fingerprint){checkoutKey='web_'+operationKey();checkoutFingerprint=fingerprint;}const r=await api('/pedidos','POST',{...body,clave_operacion:checkoutKey});cart=[];saveCart();checkoutKey=null;checkoutFingerprint=null;view='Mis pedidos';pageNumber=1;say('Pedido #'+r.data.id+' registrado. Total: '+quetzales(r.data.total)+'. No se realizó ningún cobro.');});};};
screens['Mis pedidos']=async()=>{const r=await api('/pedidos/mios?pagina='+pageNumber);main.innerHTML='<h1>Mis pedidos</h1><p>Compras de demostración, sin cobros reales.</p>'+table(r.data,[['id','Pedido'],['fecha','Fecha'],['total','Total Q'],['estado','Estado']],p=>`<button data-order="${p.id}">Ver detalle</button>`);bind('[data-order]',async b=>{const r=await api('/pedidos/'+b.dataset.order);const p=r.data;$('#modalTitle').textContent='Pedido #'+p.id;$('#fields').innerHTML=`<p>Estado: ${esc(p.estado)}</p><p>Destinatario: ${esc(p.nombre_entrega)}</p><p>Teléfono: ${esc(p.telefono_entrega)}</p><p>Dirección: ${esc(p.direccion_entrega)}</p><p>Pago: ${p.metodo_pago==='efectivo'?'Efectivo':'Tarjeta ficticia'} · Demostración</p>`+table(p.detalle,[['nombre','Producto'],['cantidad','Cantidad'],['precio_unitario','Precio unitario Q']])+`<p class="price">Total: ${quetzales(p.total)}</p>`;$('#formError').textContent='';const submit=$('#modalForm [type="submit"]');submit.disabled=true;submit.textContent='Solo consulta';$('#modalForm').onsubmit=e=>e.preventDefault();$('#modal').showModal();});pager(r.meta);};
function pointsAttempt(promo){const key='belleza.redeem.v1.'+user.id+'.'+promo;let value;try{value=sessionStorage.getItem(key);}catch{}if(!value){value='canje_'+operationKey();try{sessionStorage.setItem(key,value);}catch{}}return {key,value};}
screens.Promociones=async()=>{const client=user?.rol==='cliente';const [r,balance]=await Promise.all([api('/promociones?pagina='+pageNumber),client?api('/puntos'):Promise.resolve(null)]);const points=balance?.data.puntos??0;main.innerHTML='<h1>Promociones y beneficios</h1><p>Consulta las condiciones y vigencia de cada beneficio. Se entrega en el salón; no se descuenta automáticamente de los pedidos.</p>'+(client?`<p class="price">Tu saldo: ${esc(points)} puntos</p><button data-go="Mis puntos" class="secondary">Ver historial de puntos</button>`:'')+'<div class="grid">'+r.data.map(p=>`<article class="card"><span class="badge">${p.puntos_costo?'Canje por puntos':'Promoción'}</span><h2>${esc(p.titulo)}</h2><p>${esc(p.descripcion||'Consulta las condiciones en el salón.')}</p><p>Del ${esc(readableDate(p.fecha_inicio))} al ${esc(readableDate(p.fecha_fin))}</p>${p.descuento_porcentaje?`<p>Descuento anunciado: ${esc(p.descuento_porcentaje)}%</p>`:''}${p.puntos_costo?`<p class="price">${esc(p.puntos_costo)} puntos</p>${client?`<button data-redeem="${p.id}" ${points<p.puntos_costo?'disabled':''}>Canjear beneficio</button>${points<p.puntos_costo?`<p>Te faltan ${esc(p.puntos_costo-points)} puntos.</p>`:''}`:!user?'<button data-go="Ingresar">Ingresar para canjear</button>':'<p>Canje disponible para clientes.</p>'}`:'<p>No requiere canje de puntos. Consulta su aplicación en el salón.</p>'}</article>`).join('')+'</div>'+(r.data.length?'':'<p class="empty-state">No hay promociones vigentes en este momento.</p>');
bind('[data-redeem]',b=>{const promo=r.data.find(p=>p.id===Number(b.dataset.redeem));const attempt=pointsAttempt(promo.id);modal('Confirmar canje',[],{},async()=>{const result=await api('/puntos/canjear','POST',{promocion_id:promo.id,clave_operacion:attempt.value});try{sessionStorage.removeItem(attempt.key);}catch{}view='Mis puntos';pageNumber=1;say(result.message+'. Referencia #'+result.data.id+'.');});$('#fields').innerHTML=`<h2>${esc(promo.titulo)}</h2><p>${esc(promo.descripcion||'')}</p><p>Se utilizarán <strong>${esc(promo.puntos_costo)} puntos</strong>.</p><p>Saldo estimado después del canje: ${esc(points-promo.puntos_costo)} puntos.</p><p>El saldo y la vigencia se validan al confirmar. Recibirás el beneficio en el salón.</p><p>Si la respuesta se interrumpe, reintenta este mismo beneficio para recuperar el resultado.</p>`;$('#modalForm [type="submit"]').textContent='Confirmar canje';});pager(r.meta);};
screens['Mis puntos']=async()=>{const [saldo,h]=await Promise.all([api('/puntos'),api('/puntos/historial?pagina='+pageNumber)]);main.innerHTML=`<h1>Mis puntos</h1><article class="card"><p>Saldo disponible</p><p class="price">${esc(saldo.data.puntos)} puntos</p><p>El administrador asigna puntos por citas completadas. Las compras de productos no generan puntos automáticamente.</p><button data-go="Promociones">Explorar beneficios</button></article><h2>Historial de movimientos</h2>`+(h.data.length?h.data.map(m=>`<article class="card"><span class="badge">${Number(m.puntos)>0?'Puntos recibidos':'Canje'}</span><h3>${esc(m.motivo)}</h3><p class="price">${Number(m.puntos)>0?'+':''}${esc(m.puntos)} puntos</p><p>Fecha: ${esc(String(m.fecha||'').replace('T',' '))} · Guatemala</p><p>Referencia #${esc(m.id)}${m.cita_id?' · Cita #'+esc(m.cita_id):''}${m.promocion_id?' · Promoción #'+esc(m.promocion_id):''}</p></article>`).join(''):'<p class="empty-state">Todavía no tienes movimientos de puntos.</p>');pager(h.meta);};
const contactFields=[field('nombre','Nombre'),{...field('email','Correo','email'),optional:true},{...field('telefono','Teléfono'),optional:true}];
screens.Usuarios=async()=>{const r=await api('/admin/usuarios?pagina='+pageNumber);main.innerHTML='<h1>Usuarios</h1><button id="newUser">Registrar usuario</button>'+table(r.data,[['id','ID'],['nombre','Nombre'],['email','Correo'],['rol','Rol'],['activo','Activo']],u=>`<button data-edit="${u.id}" class="secondary">Editar</button> <button data-active="${u.id}" data-value="${!u.activo}">${u.activo?'Desactivar':'Activar'}</button>`);$('#newUser').onclick=()=>modal('Registrar usuario',[...contactFields,field('password','Contraseña inicial','password'),field('rol','Rol','select',['cliente','personal','administrador'])],{},d=>api('/admin/usuarios','POST',d));bind('[data-edit]',b=>modal('Editar usuario',contactFields,r.data.find(u=>u.id===Number(b.dataset.edit)),d=>api('/admin/usuarios/'+b.dataset.edit,'PATCH',d)));bind('[data-active]',async b=>{if(confirm('¿Cambiar el estado de esta cuenta?')){await api('/admin/usuarios/'+b.dataset.active+'/estado','PATCH',{activo:b.dataset.value==='true'});await render();}});pager(r.meta);};
const serviceFields=[field('nombre','Nombre'),{...field('descripcion','Descripción'),optional:true},field('categoria','Categoría'),field('duracion_min','Duración en minutos','number'),field('precio','Precio Q (ejemplo 135.00)')];
screens['Servicios admin']=async()=>{const r=await api('/admin/servicios?pagina='+pageNumber);main.innerHTML='<h1>Servicios del salón</h1><button id="newService">Nuevo servicio</button>'+table(r.data,[['nombre','Nombre'],['precio','Precio Q'],['duracion_min','Minutos'],['activo','Activo']],s=>`<button data-edit="${s.id}" class="secondary">Editar</button> <button data-active="${s.id}" data-value="${!s.activo}">${s.activo?'Desactivar':'Activar'}</button>`);$('#newService').onclick=()=>modal('Nuevo servicio',serviceFields,{},d=>api('/servicios','POST',d));bind('[data-edit]',b=>modal('Editar servicio',serviceFields,r.data.find(s=>s.id===Number(b.dataset.edit)),d=>api('/servicios/'+b.dataset.edit,'PUT',d)));bind('[data-active]',async b=>{await api('/servicios/'+b.dataset.active+'/estado','PATCH',{activo:b.dataset.value==='true'});await render();});pager(r.meta);};
const scheduleFields=[field('dia_semana','Día de la semana','number'),field('hora_inicio','Inicio','time'),field('hora_fin','Fin','time')];
screens.Horarios=async()=>{const people=(await api('/personal')).data;main.innerHTML='<h1>Horarios semanales</h1><p>Lunes = 1, domingo = 7. Las citas vigentes conservan su cobertura horaria.</p><div class="toolbar"><select id="professional">'+people.map(p=>`<option value="${p.id}">${esc(p.nombre)}</option>`).join('')+'</select><button id="loadSchedules">Consultar</button><button id="newSchedule">Agregar bloque</button></div><div id="scheduleTable"></div>';const load=async()=>{if(!$('#professional').value)return;const r=await api('/admin/personal/'+$('#professional').value+'/disponibilidades');$('#scheduleTable').innerHTML=table(r.data,[['dia_semana','Día'],['hora_inicio','Inicio'],['hora_fin','Fin'],['activo','Activo']],h=>`<button data-edit="${h.id}" class="secondary">Editar</button> <button data-active="${h.id}" data-value="${!h.activo}">${h.activo?'Desactivar':'Activar'}</button>`);bind('[data-edit]',b=>modal('Editar bloque',scheduleFields,r.data.find(h=>h.id===Number(b.dataset.edit)),d=>api('/admin/disponibilidades/'+b.dataset.edit,'PUT',d)));bind('[data-active]',async b=>{await api('/admin/disponibilidades/'+b.dataset.active+'/estado','PATCH',{activo:b.dataset.value==='true'});await load();});};$('#loadSchedules').onclick=()=>action(load);$('#newSchedule').onclick=()=>{const id=$('#professional').value;modal('Agregar bloque',scheduleFields,{dia_semana:1,hora_inicio:'09:00',hora_fin:'17:00'},d=>api('/personal/'+id+'/disponibilidades','POST',d));};await load();};
const productFields=[field('nombre','Nombre'),{...field('descripcion','Descripción'),optional:true},field('categoria','Categoría'),field('tipo','Tipo','select',['venta','insumo']),field('precio','Precio Q (0.00 para insumos)')];
screens.Inventario=async()=>{const r=await api('/admin/productos?pagina='+pageNumber);main.innerHTML='<h1>Productos e insumos</h1><p>Las existencias se actualizan mediante movimientos con motivo.</p><button id="newProduct">Nuevo artículo</button>'+table(r.data,[['id','ID'],['nombre','Nombre'],['tipo','Tipo'],['precio','Precio Q'],['stock','Stock'],['activo','Activo']],p=>`<button data-edit="${p.id}" class="secondary">Editar</button> <button data-move="${p.id}">Movimiento</button> <button data-active="${p.id}" data-value="${!p.activo}" class="secondary">${p.activo?'Desactivar':'Activar'}</button>`);$('#newProduct').onclick=()=>modal('Nuevo artículo',productFields,{},d=>api('/admin/productos','POST',d));bind('[data-edit]',b=>modal('Editar artículo',productFields,r.data.find(p=>p.id===Number(b.dataset.edit)),d=>api('/admin/productos/'+b.dataset.edit,'PUT',d)));bind('[data-move]',b=>modal('Movimiento de existencias',[field('tipo','Movimiento','select',['entrada','salida']),field('cantidad','Cantidad','number'),field('motivo','Motivo')],{},d=>api('/admin/inventario/movimientos','POST',{...d,producto_id:Number(b.dataset.move)})));bind('[data-active]',async b=>{await api('/admin/productos/'+b.dataset.active+'/estado','PATCH',{activo:b.dataset.value==='true'});await render();});pager(r.meta);};
screens['Pedidos admin']=async()=>{const r=await api('/admin/pedidos?pagina='+pageNumber);main.innerHTML='<h1>Pedidos de demostración</h1>'+table(r.data,[['id','Pedido'],['usuario_id','Cliente'],['fecha','Fecha'],['total','Total Q'],['estado','Estado']],p=>p.estado==='completado'?`<button data-cancel="${p.id}" class="secondary">Cancelar y reintegrar stock</button>`:'');bind('[data-cancel]',async b=>{if(confirm('¿Cancelar este pedido y devolver sus unidades al inventario?')){await api('/admin/pedidos/'+b.dataset.cancel+'/cancelar','PATCH');await render();}});pager(r.meta);};
const promoFields=[field('titulo','Título'),{...field('descripcion','Beneficio y condiciones'),optional:true},field('descuento_porcentaje','Descuento anunciado (%)','number'),field('fecha_inicio','Válida desde','date'),field('fecha_fin','Válida hasta','date'),field('puntos_costo','Puntos para canjear (0: solo publicación)','number')];
screens['Promociones admin']=async()=>{const r=await api('/admin/promociones?pagina='+pageNumber);main.innerHTML='<h1>Promociones y beneficios</h1><button id="newPromo">Nueva promoción</button>'+table(r.data,[['titulo','Título'],['fecha_inicio','Desde'],['fecha_fin','Hasta'],['puntos_costo','Puntos'],['activa','Activa']],p=>`<button data-edit="${p.id}" class="secondary">Editar</button> <button data-active="${p.id}" data-value="${!p.activa}">${p.activa?'Desactivar':'Activar'}</button>`);$('#newPromo').onclick=()=>modal('Nueva promoción',promoFields,{descuento_porcentaje:0,puntos_costo:0,fecha_inicio:dateToday(),fecha_fin:dateToday()},d=>api('/admin/promociones','POST',d));bind('[data-edit]',b=>modal('Editar promoción',promoFields,r.data.find(p=>p.id===Number(b.dataset.edit)),d=>api('/admin/promociones/'+b.dataset.edit,'PUT',d)));bind('[data-active]',async b=>{await api('/admin/promociones/'+b.dataset.active+'/estado','PATCH',{activa:b.dataset.value==='true'});await render();});pager(r.meta);};
screens['Puntos admin']=async()=>{const r=await api('/admin/puntos/historial?pagina='+pageNumber);main.innerHTML='<h1>Fidelización</h1><p>Asigna puntos una vez por cita completada, según las condiciones del salón.</p><button id="award">Asignar puntos</button>'+table(r.data,[['cliente','Cliente'],['puntos','Puntos'],['motivo','Motivo'],['fecha','Fecha']]);$('#award').onclick=()=>modal('Puntos por atención realizada',[field('cita_id','Número de cita completada','number'),field('puntos','Puntos','number'),field('motivo','Condición o motivo')],{},d=>api('/admin/puntos/asignar','POST',d));pager(r.meta);};
screens.Reportes=async()=>{main.innerHTML='<h1>Resumen del salón</h1><div class="toolbar"><label>Desde<input id="from" type="date" value="'+dateToday().slice(0,8)+'01"></label><label>Hasta<input id="to" type="date" value="'+dateToday()+'"></label><button id="loadReport">Consultar</button><button id="export" class="secondary">Exportar citas a Excel</button></div><div id="report"></div>';const period=()=>'?desde='+$('#from').value+'&hasta='+$('#to').value;const load=async()=>{const r=await api('/admin/reportes/resumen'+period());$('#report').innerHTML=`<div class="grid" style="margin-top:20px"><article class="card"><h2>Clientes activos</h2><p class="price">${r.data.clientes_activos_actuales}</p></article><article class="card"><h2>Unidades actuales</h2><p class="price">${r.data.inventario_actual.unidades}</p></article><article class="card"><h2>Ventas simuladas</h2><p class="price">Q ${esc(r.data.ventas_simuladas.total_demostracion)}</p></article></div><h2>Citas del período</h2>`+table(r.data.citas_por_estado,[['estado','Estado'],['cantidad','Cantidad']]);};$('#loadReport').onclick=()=>action(load);$('#export').onclick=()=>action(async()=>{const r=await fetch('/api/v1/admin/reportes/citas.xlsx'+period(),{headers:{Authorization:'Bearer '+token}});if(!r.ok)throw new Error((await r.json()).message);const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='citas.xlsx';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});await load();};

screens['Citas admin']=async()=>{const r=await api('/admin/citas?pagina='+pageNumber);main.innerHTML='<h1>Agenda del salón</h1>'+table(r.data,[['id','Cita'],['cliente','Cliente'],['profesional','Profesional'],['servicio','Servicio'],['fecha','Fecha'],['hora','Hora'],['estado','Estado']],c=>['pendiente','confirmada'].includes(c.estado)?`<button data-id="${c.id}" data-state="${c.estado==='pendiente'?'confirmada':'completada'}">${c.estado==='pendiente'?'Confirmar':'Completar'}</button> <button data-id="${c.id}" data-state="cancelada" class="secondary">Cancelar</button>`:'');bind('[data-state]',async b=>{if(confirm('¿Cambiar el estado de esta cita?')){await api('/admin/citas/'+b.dataset.id+'/estado','PATCH',{estado:b.dataset.state});await render();}});pager(r.meta);};

$('#menuToggle').onclick=()=>{const open=$('#nav').classList.toggle('open');$('#menuToggle').setAttribute('aria-expanded',String(open));};
document.addEventListener('click',e=>{const b=e.target.closest('[data-go]');if(b){e.preventDefault();go(b.dataset.go);}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('#nav').classList.contains('open')){$('#nav').classList.remove('open');$('#menuToggle').setAttribute('aria-expanded','false');$('#menuToggle').focus();}});
screens.Recordatorios=async()=>{const r=await api('/recordatorios');const rows=r.data.proximas_24_horas;main.innerHTML='<h1>Recordatorios</h1><p>Citas de las próximas 24 horas, en horario de Guatemala. Consulta esta sección para actualizar los avisos.</p><button id="refreshReminders" class="secondary">Actualizar</button>'+(rows.length?rows.map(c=>`<article class="card"><h2>Cita #${esc(c.id)}</h2><p>${esc(readableDate(c.fecha))} · ${esc(c.hora)}</p><span class="badge">${esc(c.estado)}</span></article>`).join(''):'<p class="empty-state">No tienes citas próximas en las siguientes 24 horas.</p>')+`<button data-go="${user.rol==='cliente'?'Mis citas':'Mi agenda'}">Ver ${user.rol==='cliente'?'mis citas':'mi agenda'}</button>`;$('#refreshReminders').onclick=()=>render();};
let clientSearch='';
screens.Clientes=async()=>{const r=await api('/admin/clientes?pagina='+pageNumber+'&q='+encodeURIComponent(clientSearch));main.innerHTML='<h1>Clientes</h1><form id="clientSearch"><label>Nombre, correo o teléfono<input name="q" maxlength="150" value="'+esc(clientSearch)+'"></label><button>Buscar</button></form>'+table(r.data,[['id','ID'],['nombre','Nombre'],['email','Correo'],['telefono','Teléfono'],['puntos','Puntos'],['activo','Activo']],c=>`<button data-client="${c.id}">Ver citas</button>`);$('#clientSearch').onsubmit=e=>{e.preventDefault();clientSearch=new FormData(e.target).get('q').trim();pageNumber=1;render();};bind('[data-client]',async b=>{const c=r.data.find(c=>c.id===Number(b.dataset.client));let p=1;const load=async()=>{const result=await api('/admin/clientes/'+c.id+'/citas?pagina='+p);$('#modalTitle').textContent='Citas de '+c.nombre;$('#fields').innerHTML=table(result.data,[['id','Cita'],['fecha','Fecha'],['hora','Hora'],['servicio','Servicio'],['estado','Estado']])+`<div class="actions"><button type="button" id="clientPrev" ${p<=1?'disabled':''}>Anterior</button><span>Página ${p}</span><button type="button" id="clientNext" ${p>=result.meta.paginas?'disabled':''}>Siguiente</button></div>`;$('#clientPrev').onclick=()=>action(async()=>{p--;await load();});$('#clientNext').onclick=()=>action(async()=>{p++;await load();});};await load();$('#formError').textContent='';$('#modalForm').onsubmit=e=>e.preventDefault();$('#modalForm [type="submit"]').disabled=true;$('#modalForm [type="submit"]').textContent='Solo consulta';$('#modal').showModal();});pager(r.meta);};
screens['Movimientos de inventario']=async()=>{const r=await api('/admin/inventario/movimientos?pagina='+pageNumber);main.innerHTML='<h1>Movimientos de inventario</h1><p>Entradas, salidas y reintegros por cancelación de pedidos.</p>'+table(r.data,[['id','ID'],['producto','Producto'],['tipo','Movimiento'],['cantidad','Cantidad'],['motivo','Motivo'],['fecha','Fecha']]);pager(r.meta);};


// ============================================================================
// SUSCRIPCIONES MENSUALES
// ============================================================================
function subscriptionPaymentFields(){
 return [
  field('metodo_pago','Método de pago','select',[
   {value:'efectivo',label:'Efectivo'},
   {value:'tarjeta_simulada',label:'Tarjeta simulada (sin cobro real)'}
  ]),
  {...field('tarjeta_ultimos4','Últimos 4 dígitos ficticios'),optional:true}
 ];
}
function normalizeSubscriptionPayment(d){
 if(d.metodo_pago==='efectivo')d.tarjeta_ultimos4=null;
 d.clave_operacion='web_'+operationKey();
 return d;
}
function subscriptionBenefitText(p){
 const items=[];
 if(Number(p.descuento_servicios||0)>0)items.push(p.descuento_servicios+'% en servicios');
 if(Number(p.descuento_productos||0)>0)items.push(p.descuento_productos+'% en productos');
 if(Boolean(p.acumulable_promociones))items.push('Acumulable con promociones');
 return items.length?items.join(' · '):'Membresía mensual';
}
screens['Mi suscripción']=async()=>{
 const [mine,plans]=await Promise.all([
  api('/suscripciones/mia'),
  api('/planes-suscripcion?pagina=1&limite=100')
 ]);
 const s=mine.data;
 if(s&&s.estado==='activa'){
  main.innerHTML='<div class="page-heading"><div><span class="eyebrow">Membresía</span><h1>Mi suscripción</h1><p>Consulta tu vigencia, beneficios y pagos.</p></div></div>'
   +'<article class="card"><span class="badge">'+esc(s.estado)+'</span><h2>'+esc(s.plan)+'</h2><p>'+esc(s.plan_descripcion||'')+'</p>'
   +'<p><strong>Precio mensual:</strong> Q '+esc(s.precio_mensual_contratado)+'</p>'
   +'<p><strong>Vigente hasta:</strong> '+esc(String(s.fecha_fin).replace('T',' ').slice(0,16))+'</p>'
   +'<p>'+esc(subscriptionBenefitText({descuento_servicios:s.descuento_servicios_contratado,descuento_productos:s.descuento_productos_contratado,acumulable_promociones:s.acumulable_promociones_contratado}))+'</p>'
   +'<div class="actions"><button id="renewSubscription">Renovar</button><button id="cancelSubscription" class="secondary">Cancelar</button></div></article>'
   +'<section class="card"><h2>Pagos</h2><div id="subscriptionPayments"></div></section>';
  $('#renewSubscription').onclick=()=>modal('Renovar suscripción',subscriptionPaymentFields(),{metodo_pago:'efectivo'},async d=>{
   const r=await api('/suscripciones/'+s.id+'/renovar','POST',normalizeSubscriptionPayment(d));
   say(r.message);
  });
  $('#cancelSubscription').onclick=()=>action(async()=>{
   if(confirm('¿Cancelar tu suscripción? Los beneficios dejarán de aplicarse inmediatamente.')){
    const r=await api('/suscripciones/'+s.id+'/cancelar','PATCH',{motivo:'Cancelación solicitada por el cliente'});
    say(r.message);await render();
   }
  });
  const payments=await api('/suscripciones/mis-pagos?pagina=1&limite=20');
  $('#subscriptionPayments').innerHTML=table(payments.data,[['fecha_pago','Fecha'],['monto','Monto Q'],['metodo_pago','Método'],['estado','Estado'],['referencia_pago','Referencia']]);
  return;
 }
 const cards=plans.data.map(p=>'<article class="card"><span class="badge">Mensual</span><h2>'+esc(p.nombre)+'</h2><p>'+esc(p.descripcion||'')+'</p><p class="price">Q '+esc(p.precio_mensual)+'</p><p>'+esc(subscriptionBenefitText(p))+'</p><button data-subscribe="'+p.id+'">Suscribirme</button></article>').join('');
 main.innerHTML='<div class="page-heading"><div><span class="eyebrow">Membresía</span><h1>Mi suscripción</h1><p>'+(s?'Tu última suscripción está '+esc(s.estado)+'. Puedes contratar un plan disponible.':'Elige un plan mensual.')+'</p></div></div><div class="grid">'+(cards||'<p class="empty-state">No hay planes disponibles.</p>')+'</div>';
 bind('[data-subscribe]',b=>modal('Contratar membresía',subscriptionPaymentFields(),{metodo_pago:'efectivo'},async d=>{
  const r=await api('/suscripciones','POST',{plan_id:Number(b.dataset.subscribe),...normalizeSubscriptionPayment(d)});
  say(r.message);
 }));
};
const subscriptionPlanFields=[
 field('nombre','Nombre'),
 {...field('descripcion','Descripción'),optional:true},
 field('precio_mensual','Precio mensual Q'),
 field('duracion_meses','Duración en meses','number'),
 field('descuento_servicios','Descuento servicios (%)','number'),
 field('descuento_productos','Descuento productos (%)','number'),
 field('acumulable_promociones','Acumulable con promociones','select',[
  {value:'false',label:'No'},
  {value:'true',label:'Sí'}
 ])
];
function normalizeSubscriptionPlan(d){
 d.acumulable_promociones=String(d.acumulable_promociones)==='true';
 return d;
}
screens['Planes suscripción']=async()=>{
 const r=await api('/admin/planes-suscripcion?pagina='+pageNumber);
 main.innerHTML='<h1>Planes de suscripción</h1><p>Configura precio, duración y beneficios.</p><button id="newSubscriptionPlan">Nuevo plan</button>'
  +table(r.data,[['id','ID'],['nombre','Nombre'],['precio_mensual','Precio Q'],['duracion_meses','Meses'],['descuento_servicios','Desc. servicios %'],['descuento_productos','Desc. productos %'],['activo','Activo']],p=>'<button data-plan-edit="'+p.id+'" class="secondary">Editar</button> <button data-plan-active="'+p.id+'" data-value="'+(!p.activo)+'">'+(p.activo?'Desactivar':'Activar')+'</button>');
 $('#newSubscriptionPlan').onclick=()=>modal('Nuevo plan',subscriptionPlanFields,{precio_mensual:'100.00',duracion_meses:1,descuento_servicios:0,descuento_productos:0,acumulable_promociones:'false'},d=>api('/admin/planes-suscripcion','POST',normalizeSubscriptionPlan(d)));
 bind('[data-plan-edit]',b=>{
  const p=r.data.find(x=>x.id===Number(b.dataset.planEdit));
  modal('Editar plan',subscriptionPlanFields,{...p,acumulable_promociones:String(Boolean(p.acumulable_promociones))},d=>api('/admin/planes-suscripcion/'+b.dataset.planEdit,'PUT',normalizeSubscriptionPlan(d)));
 });
 bind('[data-plan-active]',async b=>{await api('/admin/planes-suscripcion/'+b.dataset.planActive+'/estado','PATCH',{activo:b.dataset.value==='true'});await render();});
 pager(r.meta);
};
screens['Suscripciones admin']=async()=>{
 const r=await api('/admin/suscripciones?pagina='+pageNumber);
 main.innerHTML='<h1>Suscripciones</h1><p>Historial y vigencia de membresías.</p><button id="expireSubscriptions" class="secondary">Actualizar vencidas</button>'
  +table(r.data,[['suscripcion_id','ID'],['cliente','Cliente'],['plan','Plan'],['fecha_inicio','Inicio'],['fecha_fin','Fin'],['estado_efectivo','Estado'],['precio_mensual_contratado','Precio Q']]);
 $('#expireSubscriptions').onclick=()=>action(async()=>{const x=await api('/admin/suscripciones/marcar-vencidas','POST');say('Suscripciones actualizadas: '+x.data.suscripciones_actualizadas);await render();});
 pager(r.meta);
};
screens['Pagos suscripción']=async()=>{
 const r=await api('/admin/pagos-suscripcion?pagina='+pageNumber);
 main.innerHTML='<h1>Pagos de suscripción</h1><p>Son pagos demostrativos; no se realizan cargos bancarios reales.</p>'
  +table(r.data,[['id','ID'],['cliente','Cliente'],['suscripcion_id','Suscripción'],['periodo_inicio','Desde'],['periodo_fin','Hasta'],['monto','Monto Q'],['metodo_pago','Método'],['estado','Estado'],['referencia_pago','Referencia']]);
 pager(r.meta);
};

start();
