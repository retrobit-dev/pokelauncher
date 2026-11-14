// Load the real starter map through the real editor code and confirm every
// layer survives: this is the round trip that decides whether a map authored in
// the browser looks the same in the app.
// The editor's own working document (docs/tileset/map.json) is gitignored, so a
// clean checkout does not have it: this loads app/src/main/assets instead, which
// is the map that ends up inside the APK.
const EXPECT_COLS = 80;
const EXPECT_ROWS = 50;

const fs=require('fs'), path=require('path');
const ROOT = require('path').resolve(__dirname, '..');
const src=fs.readFileSync(path.join(ROOT,'editor/app.js'),'utf8');
class E{constructor(){this.style={};this.dataset={};this.hidden=false;this.textContent='';this.innerHTML='';
 this.classList={add(){},remove(){},toggle(){},contains(){return false}};this.children=[]}
 set id(v){this._i=v;document._byId[v]=this} get id(){return this._i}
 appendChild(c){this.children.push(c);return c} setAttribute(){} getAttribute(){}
 addEventListener(){} removeEventListener(){} setPointerCapture(){}
 getBoundingClientRect(){return{left:0,top:0,width:2560,height:1600}}
 getContext(){const n=()=>{};return{setTransform:n,fillRect:n,drawImage:n,beginPath:n,moveTo:n,
 lineTo:n,stroke:n,strokeRect:n,save:n,restore:n,rect:n,clip:n,fill:n,arc:n,
 imageSmoothingEnabled:false,canvas:{width:0,height:0}}}}
const document={_byId:{},getElementById(id){return this._byId[id]||(this._byId[id]=new E())},
 createElement(){return new E()},body:new E()};
const window={innerWidth:2560,innerHeight:1600,devicePixelRatio:1,addEventListener(){},setTimeout,clearTimeout};
const Image=class{set src(v){setTimeout(()=>this.onload&&this.onload(),0)}};
const fetch=async(u)=>{
 if(u.includes('tileset.json')) return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(ROOT,'docs/tileset/tileset.json'),'utf8'))};
 if(u.includes('map.json')) return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(ROOT,'app/src/main/assets/tileset/map.json'),'utf8'))};
 return {ok:false,json:async()=>({})};
};
const m=new Function('document','window','Image','fetch','console','setTimeout','clearTimeout',
 src+'\nreturn {boot,state,layerKey,cellSize,mapExtent,fitToScreen};')(
 document,window,Image,fetch,console,setTimeout,clearTimeout);
m.boot().then(()=>{
  const st=m.state;
  let bad=0;
  function check(l,a,e){const ok=JSON.stringify(a)===JSON.stringify(e);if(!ok)bad++;
    console.log(`  ${ok?'ok  ':'FAIL'}  ${l}${ok?'':`  (${JSON.stringify(a)} != ${JSON.stringify(e)})`}`);}
  check('peta termuat', st.loadedMap, true);
  check('ukuran peta bawaan', [st.cols, st.rows], [EXPECT_COLS, EXPECT_ROWS]);
  const expect = Object.values(JSON.parse(fs.readFileSync(path.join(ROOT,'app/src/main/assets/tileset/map.json'),'utf8')).cells)
    .reduce((n,c)=>n+Object.keys(c).length,0);
  check('setiap lapisan terbaca', st.cells.size, expect);
  // The editor must open on the file it loaded. seedIfEmpty() used to clear the
  // cells right after loadMap(), so this passed only because the shipped map
  // happened to be empty. With a map that has cells, it has to stay loaded.
  if (expect > 0) check('sel tidak dibuang setelah dimuat', st.cells.size > 0, true);
  if (expect) {
    // a tree cell must keep its grass: this is the round trip that decides
    // whether a layered map survives the editor
    const treeKey=Object.entries(JSON.parse(fs.readFileSync(path.join(ROOT,'app/src/main/assets/tileset/map.json'),'utf8')).cells)
      .find(([,c])=>c.object==='tree');
    if (treeKey) {
      const [tx,ty]=treeKey[0].split(',').map(Number);
      check('pohon ada', st.cells.get(m.layerKey(tx,ty,'object'))?.name, 'tree');
      check('rumput di bawah pohon', st.cells.get(m.layerKey(tx,ty,'ground'))?.name, treeKey[1].ground);
    }
  } else {
    // The shipped map is empty on purpose while the world is rebuilt. An empty
    // file must load as an empty editor, not be re-seeded with a default lawn.
    check('peta kosong dimuat sebagai nol sel', st.cells.size, 0);
    check('editor tidak mengisi peta kosong sendiri', st.loadedMap, true);
  }
  m.fitToScreen();
  check('zoom fit 1:1 di 2560x1600', st.zoom, 1);
  check('sel 16px', m.cellSize(), 16);
  console.log(bad?`\n${bad} gagal`:'\npeta awal termuat utuh di editor');
  process.exit(bad?1:0);
}).catch(e=>{console.log('FAIL',e.message);process.exit(1)});
