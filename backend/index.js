const express = require("express")
require("dotenv").config()
const fs = require("fs")
const {PDFParse} = require("pdf-parse")
const cors = require("cors")
const app = express()
const PORT = process.env.PORT
const multer = require("multer")
const {RecursiveCharacterTextSplitter} = require("@langchain/textsplitters")

app.use(cors())

const upload = multer({dest: "uploads/"})

app.post("/",upload.single("pdf"), async(req, res)=>{
    try{
        // Initialising TextSplitter
        const textSplitter = new RecursiveCharacterTextSplitter({
            chunkSize: 20,
            chunkOverlap: 5
        })

    const parser = new PDFParse({url: req.file.path})
    const data = await parser.getText()
    //console.log(data.text)

    const chunkedDocs = await textSplitter.splitDocuments(data)
    console.log(chunkedDocs)

    return res.json({"working": true})
    } catch(err){
        console.log(err)
        return res.json({"working": false})
    }
})

app.listen(PORT, ()=>{
    console.log("Server is started on PORT: ", PORT)
})