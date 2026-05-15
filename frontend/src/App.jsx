import { useEffect, useRef, useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'

function App() {

  const [chats, setChats] = useState([])

  const fileRef = useRef()
  const [file, setFile] = useState(null)
  const [prompt, setPrompt] = useState("")
  
  const handleSubmit = async(e)=>{
    e.preventDefault();
    const formData = new FormData()
    if(file){
    formData.append("pdf", file)
    }
    formData.append("prompt", prompt)
    setChats((prev)=>[...prev, `YOU: ${prompt}`])
    console.log(file)
    console.log(formData)
    const res = await fetch(import.meta.env.VITE_API_URI, {
      method: "POST",
      body: formData
    })
    await res.json().then((data)=>setChats((prev)=> [...prev, `AI: ${data.response}`]))
    //console.log(data)
    
    fileRef.current.value = ""
    setPrompt("")
    setFile(null)
  }

  useEffect(()=>{
    console.log("Chats->\n",chats)
  }, [chats])
  

  return (
    <>
      <form className='border flex  bottom-1 fixed-bottom' onSubmit={(e)=>handleSubmit(e)}>
        <input
         ref={fileRef}
         type="file" 
         accept= "application/pdf"
         className='border'
         onChange={(e)=>setFile(e.target.files[0])}
        />
        <input
        value={prompt}
         type="text" 
         className='border'
         onChange={(e)=>setPrompt(e.target.value)}
         />
        <button className='border'>Submit</button>
      </form>

      {chats.map((chat)=><textarea value={chat} key={Math.random()}>{chat}</textarea>)}
    </>
  )
}

export default App
