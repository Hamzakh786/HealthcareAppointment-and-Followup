"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";

export default function Doctors() {

    const [doctors,setDoctors]=useState([]);

    useEffect(()=>{

        api.get("/doctors")
        .then(res=>setDoctors(res.data.results || res.data))
        .catch(console.error)

    },[]);

    return(

        <div className="container mx-auto mt-24">

            <h1 className="text-4xl font-bold mb-8">
                Doctors
            </h1>

            <div className="grid md:grid-cols-3 gap-6">

                {doctors.map((doctor)=>(
                    <div
                        key={doctor.doctor_id}
                        className="border rounded-lg p-5 shadow"
                    >
                        <h2 className="font-bold text-xl">
                            {doctor.specialization}
                        </h2>

                        <p>{doctor.qualification}</p>

                        <p>{doctor.experience} years</p>

                    </div>
                ))}

            </div>

        </div>

    )

}