#ifndef IPEDIA_H_
#define IPEDIA_H_

#include "ipedia_Rsc.h"

#define appFileCreator          'iPED'
#define appName                 _T("iPedia")
#define appVersionNum           0x01
#define appPrefID               0x00
#define appPrefVersionNum       0x01

/* centralize all the strings that depend on the version number so that we
   don't forget update them when we update version number */
#define appVersion              _T("1.2")
/* this is what we send as our id (clientInfoField) to the server */
#define clientInfo              _T("iPedia 1.2")

#define updateCheckURL          _T("http://www.arslexis.com/updates/palm-ipedia-1-2.html")

#define appPrefDatabase   appName _T(" Prefs")

#endif /* IPEDIA_H_ */
