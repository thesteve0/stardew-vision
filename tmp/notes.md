1. Our scripts for everything besides the kserve portion create a stardew-vision namespace when they run. But we should set up vLLM first, make sure the script for it creates an Red Hat OpenShift AI (RHOAI) project titled "stardew-vision". It seems like a RHOAI project is backed by a namespace but it must have some extra metadata added. I can see the project in the normal RH OpenShift UI as a namespace, which means they add some other metadata to have it show up as an AI project in the RHOAI UI. 

2. I went with making the Connection as a URI pointed at hugging face, Option A in the instructions. What would are the pros and cons of each option?

3. For

```
Model server arguments (if there's a field):
    
--dtype=float16 --max-model-len=4096 --limit-mm-per-prompt '{"image": 1}'"
```

I don't think we need to specify the dtype, I think that was specific to the AMD Strix Halo/Point ROCm accelerator. Here we are running NVIDIA so for now, let the platform handle the defaults. 

4. Model downloaded in 217.595810755 seconds, in the documentation we should mention that it takes about 3.5 minutes to download the model. We should also investigate if there is a way to give the pods our hf token so they can download faster. 

5. Based on the screenshot I sent you for what I picked for the model deployment name (stardew-vlm), I think the internal endpoint might be http://stardew-vlm:8080/v1  
