#include <stddef.h>
#include <limits.h>
#include <libgen.h>
#include <string.h>
#include <magic.h>
#include <sqlite3ext.h>
#include <stdio.h>
SQLITE_EXTENSION_INIT1

static magic_t COOKIE = NULL;
static const char *ERROR = NULL;

static void close_magic_file_(void) {
    if( COOKIE != NULL ) {
        magic_close(COOKIE);
    }
}


static void magic_file_(sqlite3_context *ctx, int argc, sqlite3_value *argv[]) {
    const char *ans = NULL;
    char buf[PATH_MAX];

    if( ERROR != NULL ) {
        ans = ERROR;
    } else {
        strncpy(buf, sqlite3_value_text(argv[0]), PATH_MAX-1);
        ans = magic_file( COOKIE, buf );
        if( ans == NULL ) {
            ans = magic_error(COOKIE);
        }
    }
    sqlite3_result_text( ctx, ans, -1, SQLITE_TRANSIENT );
}

static void basename_(sqlite3_context *ctx, int argc, sqlite3_value *argv[]) {
    char buf[PATH_MAX];
    char *ans;
    strncpy(buf, sqlite3_value_text(argv[0]), PATH_MAX-1);
    ans = basename(buf);
    sqlite3_result_text( ctx, ans, -1, SQLITE_TRANSIENT );
}

static void dirname_(sqlite3_context *ctx, int argc, sqlite3_value *argv[]) {
    char buf[PATH_MAX];
    char *ans;
    strncpy(buf, sqlite3_value_text(argv[0]), PATH_MAX-1);
    ans = dirname(buf);
    sqlite3_result_text( ctx, ans, -1, SQLITE_TRANSIENT );
}

int sqlite3_extension_init(sqlite3 *db, char **pzErrMsg, const sqlite3_api_routines *pApi){
    int rc = SQLITE_OK;
    SQLITE_EXTENSION_INIT2(pApi);

    if( NULL == (COOKIE=magic_open(MAGIC_SYMLINK))) {
        ERROR = "[Call to libmagic:magic_open() failed]";
    } else if ( -1 == magic_load(COOKIE, NULL) ) {
        ERROR = "[Call to libmagic:magic_load() failed]";
    } else {
        atexit( close_magic_file_ );
    }

    sqlite3_create_function(db, "basename", 1, SQLITE_ANY, NULL, basename_, NULL, NULL);
    sqlite3_create_function(db, "dirname", 1, SQLITE_ANY, NULL, dirname_, NULL, NULL);
    sqlite3_create_function(db, "filetype", 1, SQLITE_ANY, NULL, magic_file_, NULL, NULL);

    return rc;
}
