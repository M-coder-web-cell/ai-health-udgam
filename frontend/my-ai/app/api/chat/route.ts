import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const apiKey = process.env.GEMINI_API_KEY;

        if (!apiKey) {
            return NextResponse.json({ message: "Running in demo mode. Please add GEMINI_API_KEY." });
        }

        // 1. Initialize SDK
        const genAI = new GoogleGenerativeAI(apiKey);

        // 2. Build system instruction
        const systemInstruction = `You are a helpful health assistant. User profile:
- Allergies: ${body.userProfile?.allergies?.join(', ') || 'None'}
- Conditions: ${body.userProfile?.conditions?.join(', ') || 'None'}
- Goals: ${body.userProfile?.goals?.join(', ') || 'None'}
Always advise consulting a professional for medical decisions.`;

        // 3. Prepare content parts
        const promptParts: any[] = [];
        
        // Add text message
        const userMessage = body.message || "Hello";
        promptParts.push({ text: userMessage });
        
        // Handle images safely
        if (body.files && Array.isArray(body.files)) {
            body.files.forEach((file: any) => {
                if (file.content && file.content.includes(',')) {
                    const base64Data = file.content.split(',')[1];
                    promptParts.push({
                        inlineData: {
                            data: base64Data,
                            mimeType: file.type || "image/jpeg"
                        }
                    });
                }
            });
        }

        // 4. Try multiple model names in order (most compatible first)
        const modelNames = [
            'gemini-2.5-flash',    // Latest flash model (user requested)
            'gemini-2.0-flash-exp', // Experimental version
            'gemini-1.5-flash',    // Previous flash version
            'gemini-1.5-pro',      // Pro version
            'gemini-1.0-pro',      // Most stable, widely available
            'gemini-pro'           // Alternative name
        ];

        let lastError: any = null;
        
        for (const modelName of modelNames) {
            try {
                console.log(`Trying model: ${modelName}`);
                
                const model = genAI.getGenerativeModel({ 
                    model: modelName,
                    systemInstruction: systemInstruction,
                    safetySettings: [
                        {
                            category: HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        },
                    ],
                });
                
                const result = await model.generateContent({
                    contents: [{ role: "user", parts: promptParts }]
                });
                
                const response = await result.response;
                const text = response.text();
                
                console.log(`Success with model: ${modelName}`);
                return NextResponse.json({ message: text });
                
            } catch (error: any) {
                console.log(`Model ${modelName} failed:`, error.message);
                lastError = error;
                // Continue to next model
            }
        }
        
        // If all models failed, throw the last error
        throw lastError || new Error('All model attempts failed');

    } catch (error: any) {
        // Detailed logging for debugging
        console.error('--- API Error Details ---');
        console.error('Error message:', error.message);
        console.error('Status:', error.status);
        if (error.stack) {
            console.error('Stack:', error.stack);
        }
        console.error('--- End Error Details ---');

        // Provide user-friendly error messages
        let errorMessage = error.message || 'Unknown error occurred';
        let statusCode = error.status || 500;

        if (errorMessage.includes('404') || errorMessage.includes('not found')) {
            errorMessage = 'The requested Gemini model is not available. This might be due to:\n' +
                '1. Your API key may not have access to certain models\n' +
                '2. The model name might be incorrect or deprecated\n' +
                '3. Your API key might need to be regenerated\n\n' +
                'Please check your Google AI Studio API key permissions or try regenerating your API key.';
            statusCode = 404;
        } else if (errorMessage.includes('API_KEY') || errorMessage.includes('authentication')) {
            errorMessage = 'Invalid or missing API key. Please check your GEMINI_API_KEY in .env file.';
            statusCode = 401;
        } else if (errorMessage.includes('quota') || errorMessage.includes('rate limit')) {
            errorMessage = 'API quota exceeded or rate limited. Please try again later.';
            statusCode = 429;
        }

        return NextResponse.json(
            { 
                error: "Failed to get response from Gemini",
                message: errorMessage,
                details: process.env.NODE_ENV === 'development' ? error.message : undefined
            },
            { status: statusCode }
        );
    }
}