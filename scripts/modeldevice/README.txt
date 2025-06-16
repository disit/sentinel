Lo script utilizza 4 funzioni e un file di configurazione.

Conf.json: contiene le informazioni necessarie alla richiesta del token, quelle relative alla creazione del modello oltre agli url usati per la creazione dei device e per l'inserimento dei dati.

Le funzioni nello script servono rispettivamente a creare il modello, il device, inserire i dati in quest'ultimo e per richiedere il token.

Se il modello o il device hanno un nome già utilizzato, la creazione fallisce e riporta la scritta "Stato creazione modello provaModel8: ko"

Quando i dati vengono inseriti correttamente, nel log viene scritto "Inserimento riuscito"
