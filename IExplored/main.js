// WinterX jailbreak apps must not run in unpatched Spring.
if (!files.exists("winterx/")) throw new Error("WinterX is not active");
var root = new UITableViewController({ title: "IExplored", style: "grouped" });
var nav = new UINavigationController(root, { barStyle: "black" });
var lastTrash = null;
function directRequest(action, path, extra, callback) {
  var base = "winterx/", full = base + path, reply = {ok:true, action:action};
  try {
    if (action === "list") {
      reply.items = files.list(full).map(function (name) {
        var folder = name.charAt(name.length - 1) === "/";
        var clean = folder ? name.slice(0, -1) : name;
        return {name:clean, directory:folder, size:null};
      }).sort(function (a,b) { return a.directory === b.directory ? a.name.localeCompare(b.name) : (a.directory ? -1 : 1); });
    } else if (action === "read") reply.text = files.read(full);
    else if (action === "write") files.write(full, extra.text);
    else if (action === "mkdir") files.mkdir(full);
    else if (action === "trash") {
      var token = String(Date.now()) + "-" + String(Math.floor(Math.random() * 1000000000));
      files.mkdir(base + "ruby/iexplored-trash");
      files.move(full, base + "ruby/iexplored-trash/" + token);
      storage.set("iexplored.trash." + token, path);
      reply.token = token;
    } else if (action === "restore") {
      var original = storage.get("iexplored.trash." + extra.token);
      if (!original) throw new Error("The original location is unknown.");
      files.move(base + "ruby/iexplored-trash/" + extra.token, base + original);
      storage.remove("iexplored.trash." + extra.token);
    } else throw new Error("Unsupported file operation.");
    if (callback) callback(reply);
  } catch (e) { UIAlertView.show({title:"File Error",message:String(e),buttons:["OK"]}); }
}
function request(action, path, extra, callback) {
  directRequest(action, path, extra, callback);
}

function join(path, name) { return path ? path + "/" + name : name; }
function editText(path, text) {
  var page = new UIViewController({title:path.split('/').pop(), background:"#ffffff"});
  var editor = page.add(new UITextView({frame:[0,0,320,365], text:text, editable:true, size:14}));
  page.add(new UIButton({frame:[90,370,140,42],title:"Save",onTap:function(){
    UIAlertView.show({title:"Save File?",message:"This will replace the current file contents.",buttons:["Cancel","Save"]},function(index){
      if (index === 1) request("write",path,{text:editor.text},function(){UIAlertView.show({title:"Saved",message:"File saved.",buttons:["OK"]});});
    });
  }}));
  nav.push(page);
}
function itemPage(path, item, refresh) {
  var full = join(path, item.name);
  var page = new UITableViewController({title:item.name,style:"grouped",sections:[{header:"FILE",rows:[
    {title:item.name,subtitle:item.directory ? "Folder" : (item.size == null ? "File" : String(item.size) + " bytes"),selectable:false},
    {title:item.directory ? "Open Folder" : "Open Text File",accessory:"disclosure",onSelect:function(){
      if (item.directory) browse(full, item.name);
      else request("read",full,null,function(reply){editText(full,reply.text);});
    }},
    {title:"Move to Trash",accessory:"disclosure",onSelect:function(){
      UIAlertView.show({title:"Move to Trash?",message:"You can restore the last item from IExplored.",buttons:["Cancel","Move"]},function(index){
        if (index === 1) request("trash",full,null,function(reply){lastTrash=reply.token; storage.set("iexplored.last-trash",lastTrash); nav.pop(); refresh();});
      });
    }}
  ]}]});
  nav.push(page);
}
function browse(path, title, isRoot) {
  var page = isRoot ? root : new UITableViewController({title:title,style:"grouped"});
  function refresh() {
    request("list", path, null, function(reply) {
      var rows = reply.items.map(function(item){return {title:item.name,subtitle:item.directory ? "Folder" : (item.size == null ? "File" : String(item.size) + " bytes"),accessory:"disclosure",onSelect:function(){itemPage(path,item,refresh);}};});
      page.sections=[{header:"ACTIONS",rows:[
        {title:"Refresh",accessory:"disclosure",onSelect:refresh},
        {title:"New Folder…",accessory:"disclosure",onSelect:function(){
          UIAlertView.show({title:"New Folder",message:"Enter a name.",field:"Folder name",buttons:["Cancel","Create"]},function(index,name){
            if(index===1 && name) request("mkdir",join(path,name),null,refresh);
          });
        }},
        {title:"Restore Last Removed Item",accessory:"disclosure",onSelect:function(){
          var token=storage.get("iexplored.last-trash");
          if (!token) { UIAlertView.show({title:"Nothing to Restore",message:"No removed item is recorded.",buttons:["OK"]});return; }
          request("restore","",{token:token},function(){storage.remove("iexplored.last-trash");lastTrash=null;refresh();});
        }}
      ]},{header:"SPRING FILES",rows:rows.length?rows:[{title:"Empty Folder",selectable:false}]}];
    });
  }
  page.sections=[{rows:[{title:"Loading…",selectable:false}]}];
  page.onAppear=refresh;
  if (!isRoot) nav.push(page);
}
browse("","IExplored",true);
UIApplication.run(nav);
// Spring may not fire onAppear for the first root controller.
setTimeout(function () { root.onAppear(); }, 200);
