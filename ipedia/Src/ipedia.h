#ifndef IPEDIA_H_
#define IPEDIA_H_

#include "ipedia_Rsc.h"

#define appFileCreator          'iPED'
#define appName                 _T("iPedia")
#define appPrefID               0x00
#define appPrefVersionNum       0x01

/* centralize all the strings that depend on the version number so that we
   don't forget update them when we update version number */
#define appVersion              _T("1.3")
/* this is what we send as our id (clientInfoField) to the server */
#define clientInfo              _T("iPedia 1.3")

#define pocketPCClientInfo      _T("PocketPC 1.2")
#define smartphoneClientInfo    _T("Smartphone 1.2")

#define updateCheckURL          _T("http://www.arslexis.com/updates/palm-ipedia-1-3.html")

#define appPrefDatabase   appName _T(" Prefs")

#endif /* IPEDIA_H_ */
