#include "Logging.hpp"
#include "Application.hpp"
#include <limits>

namespace ArsLexis
{

    void Logger::log(const char* text, uint_t length)
    {
        String full;
        // 8=timestamp; 1=tab; 2=braces; 1=colon; 1=tab; 1=newline; 1=null
        full.reserve(8+1+2+contextLength_+1+1+length+1+1);
        char buffer[9];
        UInt32 timestamp=TimGetTicks();
        StrPrintF(buffer, "%lx", timestamp);
        full.append(buffer, 8).append("\t[", 2).append(context_, contextLength_).append("]:\t", 3).append(text, length).append(1, '\n');
        logRaw(full);
    }

    RootLogger* RootLogger::instance()
    {
        RootLogger* logger=0;
        //! @todo Implement static instance retrieval using FtrGet().
        
        return logger;
    }

    FunctionLogger::FunctionLogger(const char* context, Logger& parent):
        ChildLogger(context, parent)
    {
        log(">>> Enter");
    }
        

    FunctionLogger::FunctionLogger(const char* context):
        ChildLogger(context)
    {
        log(">>> Enter");
    }
    
    FunctionLogger::~FunctionLogger()
    {
        log("<<< Exit");
    }

#pragma mark -
#pragma mark HostFileLogSink    

    HostFileLogSink::HostFileLogSink(const char* fileName):
        file_(HostFOpen(fileName, "w"))
    {}
    
    HostFileLogSink::~HostFileLogSink()
    {
        if (file_)
        {
            HostFFlush(file_);
            HostFClose(file_);
        }
    }
    
    void HostFileLogSink::output(const String& str)
    {
        if (file_)
        {
            HostFPutS(str.c_str(), file_);
            HostFFlush(file_);
        }
    }

#pragma mark -
#pragma mark MemoLogSink

    MemoLogSink::MemoLogSink():
        db_(NULL)
    {
        db_=DmOpenDatabaseByTypeCreator('DATA', 'memo', dmModeReadWrite);
        if (NULL==db_)
        {
            Err error=DmGetLastErr();
        }
    }
    
    void MemoLogSink::closeDatabase()
    {
        DmCloseDatabase(db_);
        db_=NULL;
    }
    
    MemoLogSink::~MemoLogSink()
    {
        if (db_)
            closeDatabase();
    }
    
    void MemoLogSink::output(const String& str)
    {
        if (!db_)
            return;
        UInt16 index=dmMaxRecordIndex;
        const char* text=str.c_str();
        UInt16 len=StrLen(text)+1;
        MemHandle handle=DmNewRecord(db_, &index, len);
        if (!handle)
        {
            closeDatabase();
            return;
        }
        void* data=MemHandleLock(handle);
        if (data)
        {
            DmWrite(data, 0, text, len);
            MemHandleUnlock(handle);
        }
        DmReleaseRecord(db_, index, true);
    }

}
