/* Export the recorded native scene. sharp is optional and only needed for PNG. */
const fs=require('fs'),path=require('path'),os=require('os');
const root=path.resolve(__dirname,'..'),output=path.join(root,'results/prototype');
const config=path.join(os.tmpdir(),'city-fontconfig.conf');
fs.writeFileSync(config,'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><dir>/usr/share/fonts</dir><cachedir>/tmp/city-font-cache</cachedir></fontconfig>');
process.env.FONTCONFIG_FILE=config;
let sharp;try{sharp=require('sharp');}catch{sharp=require('/opt/homeops/games/web/node_modules/sharp');}
Promise.all(['map-preview','map-closeup','map-mobile'].map(async name=>{
 const input=path.join(output,name+'.svg');if(!fs.existsSync(input))return;
 await sharp(input).png().toFile(path.join(output,name+'.png'));console.log(name+'.png');
})).catch(error=>{console.error(error);process.exitCode=1;});
